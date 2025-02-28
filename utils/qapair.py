# -*- coding: utf-8 -*-
# @Time : 2025/2/26 下午3:23
# @Author : renjiajia
from typing import Dict
import os
import pandas as pd
from utils.logger import logger


class QAPairManager:
    """管理问答对的类，优化Excel读写操作"""
    def __init__(self, file_path: str = 'data/qa_pairs.xlsx'):
        self.file_path = file_path
        self.qa_pairs: Dict[str, Dict[str, str]] = self._load_qa_pairs()

    def _load_qa_pairs(self) -> Dict[str, Dict[str, str]]:
        """加载现有的QA对"""
        try:
            if not os.path.exists(self.file_path):
                # 如果文件不存在，创建空文件并初始化表头
                df = pd.DataFrame(columns=["question", "sql", "answer"])
                df.to_excel(self.file_path, index=False)
                return {}
            df = pd.read_excel(self.file_path, engine='openpyxl')
            return df.set_index("question").to_dict(orient="index") if not df.empty else {}
        except Exception as e:
            logger.error(f"加载QA对失败: {e}")
            return {}

    def update(self, question: str, sql: str, answer: str) -> None:
        """以追加方式更新QA对"""
        try:
            # 检查问题是否已存在
            if question in self.qa_pairs:
                # 更新内存中的数据
                self.qa_pairs[question]["sql"] = sql
                self.qa_pairs[question]["answer"] = answer
                # 读取现有Excel文件
                df = pd.read_excel(self.file_path, engine='openpyxl')
                # 更新对应行的值
                df.loc[df['question'] == question, ['sql', 'answer']] = [sql, answer]
            else:
                # 更新内存中的数据
                self.qa_pairs[question] = {"sql": sql, "answer": answer}
                # 创建新行
                new_row = pd.DataFrame({
                    "question": [question],
                    "sql": [sql],
                    "answer": [answer]
                })
                # 使用ExcelWriter以追加模式写入
                with pd.ExcelWriter(self.file_path, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
                    # 读取现有数据
                    existing_df = pd.read_excel(self.file_path, engine='openpyxl')
                    # 合并新旧数据
                    df = pd.concat([existing_df, new_row], ignore_index=True)
                    # 写入文件
                    df.to_excel(writer, index=False)

            logger.info(f"更新QA对: {question}")
        except Exception as e:
            logger.error(f"更新QA对失败: {e}")

    def save_to_excel(self) -> None:
        """可选方法：将内存中的所有数据保存到Excel"""
        try:
            df = pd.DataFrame.from_dict(self.qa_pairs, orient="index").reset_index()
            df.columns = ["question", "sql", "answer"]
            df.to_excel(self.file_path, index=False)
            logger.info("保存所有QA对到Excel")
        except Exception as e:
            logger.error(f"保存QA对到Excel失败: {e}")


if __name__ == '__main__':
    qapair = QAPairManager()
    qapair.update("what is your name", "select name from user where id = 1", "my name is tom")
    qapair.update("what is your age", "select age from user where id = 1", "I am 18 years old")
    qapair.update("what is your sex", "select sex from user where id = 1","I am a boy")