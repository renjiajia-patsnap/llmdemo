# -*- coding: utf-8 -*-
# @Time : 2025/3/4 下午3:23
# @Author : renjiajia
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from functools import lru_cache
from utils.qapair import QAPairManager
from typing import Dict, Any
from langchain.schema import Document
from utils.logger import logger

# 加载 OpenAI 的嵌入模型
embeddings = OpenAIEmbeddings()
qa_manager = QAPairManager(file_path='data/qa_pairs2.xlsx')

class QuestionSimilaritySearcher:
    def __init__(self):
        self.vector_store = None
        self.processed_questions = set()
        self._embeddings = embeddings  # 使用全局的 embeddings

    def _initialize_vector_store(self, docs):
        """初始化向量存储"""
        if not docs:
            return
        self.vector_store = FAISS.from_documents(docs, self._embeddings)
        self.processed_questions = {doc.page_content for doc in docs}

    def _update_vector_store(self, new_docs):
        """增量更新向量存储"""
        if not new_docs:
            return
        new_docs_to_add = [doc for doc in new_docs
                           if doc.page_content not in self.processed_questions]
        if new_docs_to_add:
            if self.vector_store is None:
                self.vector_store = FAISS.from_documents(new_docs_to_add, self._embeddings)
            else:
                self.vector_store.add_documents(new_docs_to_add)
            self.processed_questions.update(doc.page_content for doc in new_docs_to_add)

    @staticmethod
    def find_similar_question(input: Dict[str, Any]) -> Dict[str, Any]:
        """
        根据输入问题查找相似的问题，使用缓存的向量存储并支持增量更新。
        """
        searcher = QuestionSimilaritySearcher._get_searcher()

        logger.info("Finding similar question beginning>>>>>>>>>>>>>>>>>>>>>>>>")
        logger.info("find_similar_question input: %s", input)

        user_question = input.get("question", "")
        docs = [Document(page_content=q, metadata=info)
                for q, info in qa_manager.qa_pairs.items()]

        if not docs:
            return {"question": user_question, "answer": ""}

        if searcher.vector_store is None:
            searcher._initialize_vector_store(docs)
        else:
            searcher._update_vector_store(docs)

        results = searcher.vector_store.similarity_search_with_score(user_question, k=1)
        similar_score = 1 - results[0][1] if results else 0

        if results and similar_score > 0.95:
            logger.info("Found similar question: %s", results[0][0].page_content)
            logger.info("Similarity score: %s", similar_score)
            logger.info("Finding similar question end>>>>>>>>>>>>>>>>>>>>>>>>")
            return {
                "sql": results[0][0].metadata['sql'],
                "answer": results[0][0].metadata['answer'],
                "question": user_question
            }

        logger.info("No similar question found")
        logger.info("Finding similar question end>>>>>>>>>>>>>>>>>>>>>>>>\n\n")
        return {"question": user_question, "answer": ""}

    @staticmethod
    @lru_cache(maxsize=1)
    def _get_searcher():
        """单例模式获取 searcher 实例"""
        return QuestionSimilaritySearcher()

if __name__ == '__main__':
    input = {"question": "what is your name"}
    result = QuestionSimilaritySearcher.find_similar_question(input)
    print(result)