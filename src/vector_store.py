import os
import ssl
ssl._create_default_https_context = ssl._create_unverified_context
os.environ["HF_HUB_DISABLE_SSL_VERIFY"] = "1"
os.environ["HF_HUB_OFFLINE"] = "1"

import hashlib
import glob
import chromadb
from chromadb.utils import embedding_functions

class ObsidianVectorStore:
    def __init__(self, api_key, vault_path, db_path="./chroma_db"):
        self.vault_path = vault_path
        self.db_path = db_path

        class LocalEmbeddingFunction(embedding_functions.EmbeddingFunction):
            def __init__(self):
                from sentence_transformers import SentenceTransformer
                # local_files_only=True 强制仅用本地缓存，不联网
                self.model = SentenceTransformer(
                    'all-MiniLM-L6-v2',
                    local_files_only=True
                )
            def __call__(self, texts):
                if isinstance(texts, str):
                    texts = [texts]
                embeddings = self.model.encode(texts, show_progress_bar=False)
                return embeddings.tolist()

        self.chroma_client = chromadb.PersistentClient(path=db_path)
        self.embedding_fn = LocalEmbeddingFunction()

        self.collection = self.chroma_client.get_or_create_collection(
            name="obsidian_notes",
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        self.is_indexed = False

    def get_document_id(self, file_path):
        return hashlib.md5(file_path.encode()).hexdigest()

    def index_vault(self, force_rebuild=False):
        if not os.path.exists(self.vault_path):
            print(f"Obsidian路径不存在: {self.vault_path}")
            return
        if force_rebuild:
            print("强制重建索引...")
            self.chroma_client.delete_collection("obsidian_notes")
            self.collection = self.chroma_client.get_or_create_collection(
                name="obsidian_notes",
                embedding_function=self.embedding_fn,
                metadata={"hnsw:space": "cosine"}
            )
        if self.collection.count() > 0:
            print(f"向量库已有 {self.collection.count()} 条笔记")
            self.is_indexed = True
            return
        md_files = glob.glob(os.path.join(self.vault_path, "**", "*.md"), recursive=True)
        print(f"扫描到 {len(md_files)} 个 Markdown 文件")
        documents, ids, metadatas = [], [], []
        for file_path in md_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read().strip()
                if len(content) > 100:
                    rel_path = os.path.relpath(file_path, self.vault_path)
                    doc_id = self.get_document_id(file_path)
                    documents.append(content)
                    ids.append(doc_id)
                    metadatas.append({"source": rel_path, "filename": os.path.basename(file_path)})
            except:
                pass
        if documents:
            batch_size = 50
            for i in range(0, len(documents), batch_size):
                print(f"  索引批次 {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}...")
                self.collection.add(
                    documents=documents[i:i+batch_size],
                    ids=ids[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size]
                )
            print(f"索引完成，添加 {len(documents)} 条笔记")
        else:
            print("没有符合条件的笔记")
        self.is_indexed = True

    def retrieve_similar(self, query, n_results=3):
        if not self.is_indexed and self.collection.count() == 0:
            return [], []
        try:
            results = self.collection.query(query_texts=[query], n_results=n_results)
            docs = results['documents'][0] if results['documents'] else []
            metas = results['metadatas'][0] if results['metadatas'] else []
            return docs, metas
        except Exception as e:
            print(f"检索失败: {e}")
            return [], []

    def add_document(self, text, doc_id, metadata=None):
        self.collection.add(documents=[text], ids=[doc_id], metadatas=[metadata] if metadata else None)

    def get_stats(self):
        return {"total_notes": self.collection.count()}