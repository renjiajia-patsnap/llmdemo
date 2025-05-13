# -*- coding: utf-8 -*-
# @Time : 2025/3/7 上午11:01
# @Author : renjiajia
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from typing import Optional, Union, Iterator
import os

load_dotenv()


class LLMClient:
    # 定义每个模型支持的配置
    MODEL_CONFIG = {
        "tongyi": {
            "base_url": os.getenv('tongyi_base_url'),
            "api_key": os.getenv('tongyi_api_key'),
            "supported_models": ["qwq-plus"],
            "requires_streaming": True,  # 通义千问可能需要流式输出
        },
        "deepseek": {
            "base_url": os.getenv('deepseek_base_url'),
            "api_key": os.getenv('deepSeek_api_key'),
            "supported_models": ["deepseek-chat", "deepseek-reasoner"],
            "requires_streaming": False,  # 根据实际情况调整
        },
        "openai": {
            "base_url": os.getenv('openai_base_url'),
            "api_key": os.getenv('openai_api_key'),
            "supported_models": ["gpt-3.5-turbo", "gpt-4", "o3-mini"],
            "requires_streaming": False,  # OpenAI 通常支持非流式，但也支持流式
        },
    }

    def __init__(self, model_type: str, model_name: Optional[str] = None, streaming: bool = False):
        """
        初始化 LLMClient 实例。

        :param model_type: 模型类型，如 "tongyi", "deepseek", "openai"
        :param model_name: 模型名称，如 "qwen-plus", "deepseek-chat", "gpt-3.5-turbo"
        :param streaming: 是否启用流式输出，默认为 False
        """
        self.model_type = model_type
        self.model_name = model_name
        self.streaming = streaming

        # 校验模型类型是否支持
        if self.model_type not in self.MODEL_CONFIG:
            raise ValueError(f"不支持的模型类型: {self.model_type}")

        # 如果传入了 model_name，校验是否是该模型支持的类型
        config = self.MODEL_CONFIG[self.model_type]
        if self.model_name and self.model_name not in config["supported_models"]:
            raise ValueError(
                f"模型类型 {self.model_type} 不支持 {self.model_name}，支持的模型为: {config['supported_models']}"
            )

        # 检查是否需要强制流式输出
        if config.get("requires_streaming", False) and not self.streaming:
            print(f"警告: {self.model_type} 模型需要流式输出，已自动启用 streaming=True")
            self.streaming = True

    def get_model(self) -> ChatOpenAI:
        """创建并返回配置好的 ChatOpenAI 实例"""
        config = self.MODEL_CONFIG[self.model_type]

        # 如果未传入 model_name，使用默认模型
        if not self.model_name:
            self.model_name = config["supported_models"][0]  # 使用第一个支持的模型作为默认值

        # 配置 headers，deepseek 不需要额外的 headers
        default_headers = (
            {} if self.model_type == "deepseek" else {"X-Ai-Engine": "openai"}
        )

        return ChatOpenAI(
            default_headers=default_headers,
            base_url=config["base_url"],
            api_key=config["api_key"],
            model=self.model_name,
            streaming=self.streaming,  # 启用流式输出支持
        )

    def invoke(self, prompt: str) -> Union[str, Iterator[str]]:
        """
        调用模型并返回结果，支持流式和非流式输出。

        :param prompt: 输入的提示词
        :return: 如果 streaming=True，返回流式迭代器；否则返回完整字符串
        """
        model = self.get_model()
        if self.streaming:
            return self._stream_response(model, prompt)
        else:
            response = model.invoke(prompt)
            return response.content if hasattr(response, 'content') else str(response)

    def _stream_response(self, model: ChatOpenAI, prompt: str) -> Iterator[str]:
        """
        处理流式输出，返回内容迭代器。

        :param model: ChatOpenAI 实例
        :param prompt: 输入的提示词
        :return: 流式内容的迭代器
        """
        for chunk in model.stream(prompt):
            yield chunk.content if hasattr(chunk, 'content') else str(chunk)


# 示例用法
if __name__ == "__main__":
    # 非流式输出示例
    # client = LLMClient(model_type="openai", model_name="gpt-3.5-turbo", streaming=False)
    # result = client.invoke("你好，介绍一下自己")
    # print("非流式输出:", result)
    prompt = """
    请分析用户的自然语言问题，分析用户问题意图。问题如下：
    帮我找几条专利延长类型为PTE，并且关联的药物不为空，返回专利id及关联的药物ID，延长类型？
    
    可用表信息：
    [('ads_phs_patent_text_type', '中英文专利文本分类业务表'), ('ads_phs_drug_deal', '交易业务表'), ('ads_phs_dmp_drug_deal_sub_event', 'dmp交易子事件检索大宽表'), ('ads_phs_da_cde', 'CDE业务表'), ('ads_phs_cr_biomarker', '生物标志物(实体)业务表'), ('ads_phs_drug_special_approval_tuple', '特殊审评二元组业务表'), ('ads_phs_patent_fda', 'fda 专利业务表'), ('ads_phs_patent_technology', '专利技术分类业务表'), ('ads_phs_dmp_drug', '药物检索大宽表'), ('ads_phs_ct', '临床业务表'), ('ads_phs_patent_entity_rel', 'LS 专利关系业务表'), ('ads_phs_cr', '临床结果业务表'), ('ads_phs_tm', '转化医学业务表'), ('ads_phs_dmp_cr', '临床结果检索大宽表'), ('ads_phs_da_cde_special_approval', 'CDE特殊审批品种业务表'), ('ads_phs_dmp_dev_status', '研发状态（业务表）检索大宽表'), ('ads_phs_da_base', '药物审批基础业务表;ads'), ('ads_phs_dmp_ct', '临床检索大宽表'), ('ads_phs_dmp_dev_status_detail', '药物研发状态明细检索表'), ('ads_phs_target', '靶点业务表'), ('ads_phs_pub_name', 'PHS名称明细表'), ('ads_phs_patent_extension', '专利延期业务表'), ('ads_phs_dmp_tm', 'dmp转化医学检索大宽表'), ('ads_phs_drug', '药物业务表'), ('ads_phs_paper_rel', 'pharm 文献关系明细表'), ('ads_phs_drug_deal_translation', '交易业务翻译表'), ('ads_phs_dmp_biomarker', '生物标记物检索大宽表'), ('ads_phs_da_cde_breakthrough_therapy', 'CDE突破性治疗公示业务表'), ('ads_phs_patent_recommend', '专利推荐业务表'), ('ads_phs_da_cde_acceptance_progress', 'CDE受理进度业务表'), ('ads_phs_dmp_drug_deal', 'dmp交易检索大宽表'), ('ads_phs_patent_cde', 'cde 专利业务表'), ('ads_phs_dmp_target', '靶点大宽表'), ('ads_phs_dmp_news', '新闻检索大宽表'), ('ads_phs_drug_mechanism_action', '作用机制业务表'), ('ads_phs_tm_translation', '转化医学业务翻译表'), ('ads_phs_cr_endpoint', '终点指标(实体)业务表'), ('ads_phs_drug_chemical_rel', '药物结构关系业务表'), ('ads_phs_cr_group_list', '临床结果分组业务表'), ('ads_phs_cr_outcome_measure', '临床结果终点指标业务表'), ('ads_phs_pub_multi_source_rel', '公共实体关系表'), ('ads_phs_org', 'pharm机构业务表'), ('ads_phs_da_cde_priority_review', 'CDE优先审评公示业务表'), ('ads_phs_cr_baseline_measure', '临床结果基线业务表'), ('ads_phs_da_cde_trinity_publicity', 'CDE三合一序列公示业务表'), ('ads_phs_patent_dosage_form', 'PHS 专利剂型业务表'), ('ads_phs_report', '报告信息'), ('ads_phs_drug_milestone', '药物Milestone业务表'), ('ads_phs_da_cde_delivery_info', 'CDE送达信息业务表'), ('ads_phs_pub_entity_migration_record', '实体迁移记录业务表'), ('ads_phs_da_product', '药物审批product业务表;ads'), ('ads_phs_da_cde_acceptance_variety', 'CDE受理品种信业务表'), ('ads_phs_pub_annotation', '公共标注表;ads'), ('ads_phs_cr_translation', '临床结果翻译业务表'), ('ads_phs_da_cde_ct_imply_license', 'CDE临床默示许可业务表'), ('ads_phs_drug_special_approval', '药物特殊审评业务表'), ('ads_phs_da_submission', '药物审批submission业务表;ads'), ('ads_phs_dmp_drug_approval', ''), ('ads_phs_dmp_disease', '适应症检索大宽表'), ('ads_phs_ct_translation', '临床业务翻译表'), ('ads_phs_target_extend', '多靶点业务表'), ('ads_phs_disease', '适应症业务表'), ('ads_phs_dmp_endpoint', '终点指标检索大宽表'), ('ads_phs_da_cde_review_task_publicity', 'CDE审评任务公示业务表'), ('ads_phs_pub_entity_count', '实体 count 业务表'), ('ads_phs_kg_relationship_inc_daily', ''), ('ads_phs_drug_dev_status', '研发状态业务表'), ('ads_phs_dmp_mechanism', '作用机制大宽表')]
    
    返回JSON：{'intent': '意图', 'tables': ['表1', '表2']}
    """
    prompt2 = """
    您是旨在与TiDB（兼容 MySQL 5.7 的分布式数据库） 数据库交互的代理。给定一个输入问题，创建一个语法正确的 MySQL 查询。
    除非用户指定了他们希望获取的特定数量的示例，否则请始终将查询限制为最多 5 个结果。
    您可以按相关列对结果进行排序，以返回数据库中最相关示例。
    永远不要查询特定表中的所有列，只询问给定问题的相关列。不要对数据库进行任何 DML 语句（INSERT、UPDATE、DELETE、DROP 等）。
    如果问题似乎与数据库无关，只需返回 “I don't know” 作为答案。
    特别注意：对于涉及多个表的问题，请使用 JOIN 语句来连接相关表，并确保查询语句包含所有必要的表和字段。
    用户意图：查询专利延期记录中，筛选出延期类型为PTE且关联的药物字段不为空的记录，并返回这些记录的专利id、关联的药物ID以及延期类型字段。
    可能相关的业务表信息如下：
    {'ads_phs_patent_extension': '表名：ads_phs_patent_extension\n表结构：CREATE TABLE `ads_phs_patent_extension` (\n  `patent_id` varchar(64) NOT NULL COMMENT \'专利id\',\n  `extension_id` varchar(64) NOT NULL COMMENT \'专利延期id\',\n  `extension_apno` varchar(64) NOT NULL COMMENT \'spc/us_pte/us_pte_app/jp_pte,jp的apno号\',\n  `applicant` text DEFAULT NULL COMMENT \'申请机构名称\',\n  `authority_country` varchar(64) DEFAULT NULL COMMENT \'受理国家\',\n  `authority_region_id` varchar(64) DEFAULT NULL COMMENT \'申请国家 对应的region_id\',\n  `drug_id` json DEFAULT NULL COMMENT \'药物id\',\n  `product` json DEFAULT NULL COMMENT \'product文本\',\n  `indication` text DEFAULT NULL COMMENT \'特定用途\',\n  `extension_status` json DEFAULT NULL COMMENT \'延期状态\',\n  `maximum_expiry_date` varchar(32) DEFAULT NULL COMMENT \'最晚到期日\',\n  `extension_time` json DEFAULT NULL COMMENT \'授予的延长时间\',\n  `filing_date` varchar(64) DEFAULT NULL COMMENT \'spc申请日期\',\n  `in_force_date` varchar(32) DEFAULT NULL COMMENT \'授予延长/补偿的生效日\',\n  `actual_expiry_date` varchar(32) DEFAULT NULL COMMENT \'实际到期日\',\n  `invalid_date` varchar(32) DEFAULT NULL COMMENT \'延长失效日期\',\n  `lapsed_date` varchar(32) DEFAULT NULL COMMENT \'延长终止日\',\n  `granted_date` varchar(32) DEFAULT NULL COMMENT \'延长授权日\',\n  `refused_date` varchar(32) DEFAULT NULL COMMENT \'延长驳回日\',\n  `revoked_date` varchar(32) DEFAULT NULL COMMENT \'延长撤销日\',\n  `ped` int(1) DEFAULT NULL COMMENT \' 是否儿科实验的6个月延长\',\n  `url` varchar(255) DEFAULT NULL COMMENT \'详情页地址\',\n  `pdf_url` json DEFAULT NULL COMMENT \'爬取的pdf的s3地址\',\n  `extension_type` varchar(32) DEFAULT NULL COMMENT \'数据来源\',\n  `inpadoc_number` varchar(64) DEFAULT NULL COMMENT \'inpadoc_number\',\n  `ped_expiry_date` varchar(32) DEFAULT NULL COMMENT \'ped 过期时间\',\n  `ped_status` json DEFAULT NULL COMMENT \'ped 状态\',\n  `ped_filling_date` varchar(32) DEFAULT NULL COMMENT \'ped 申请日期\',\n  `ped_granted_date` varchar(32) DEFAULT NULL COMMENT \'ped 申请日期\',\n  `ped_refused_date` varchar(32) DEFAULT NULL COMMENT \'ped 延长驳回日\',\n  `ped_revoked_date` varchar(32) DEFAULT NULL COMMENT \'ped 延长撤销日\',\n  `authorization_des` json DEFAULT NULL COMMENT \'药物批准号和获批日期\',\n  `data_status` varchar(64) NOT NULL DEFAULT \'ACTIVE\' COMMENT \'数据状态\',\n  `created_ts` timestamp DEFAULT CURRENT_TIMESTAMP,\n  `updated_ts` timestamp DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,\n  PRIMARY KEY (`patent_id`,`extension_id`) /*T![clustered_index] CLUSTERED */,\n  KEY `idx_extension_id` (`extension_id`)\n) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin COMMENT=\'专利延期业务表\'\n示例数据：[{\'extension_status\': \'["LAPSED"]\', \'drug_id\': \'["836b5d60fa984b3fa4af638bf0fdf9d0"]\', \'authorization_des\': \'[{"authorization_date": "20090515", "authorization_number": "EU/1/09/522"}]\', \'extension_apno\': \'spc\', \'ped\': \'0\', \'created_ts\': \'1733223672000\', \'authority_country\': \'AT\', \'data_status\': \'ACTIVE\', \'extension_id\': \'18/2009\', \'updated_ts\': \'1733223672000\', \'patent_id\': \'0000bd07-b6b3-44fc-9b4c-951686a701aa\', \'product\': \'[{"lang": "AT", "name": "ULIPRISTAL-ACETAT"}]\', \'maximum_expiry_date\': \'20140623\', \'extension_type\': \'SPC\'}, {\'extension_status\': \'["GRANTED"]\', \'drug_id\': \'["093e34ca7fc84af38142e5e3774251ef"]\', \'authorization_des\': \'[{"authorization_date": "20200810", "authorization_number": "EU/1/20/1455"}]\', \'extension_apno\': \'spc\', \'ped\': \'0\', \'created_ts\': \'1720611311000\', \'authority_country\': \'NO\', \'data_status\': \'ACTIVE\', \'extension_id\': \'2020037\', \'updated_ts\': \'1733223615000\', \'patent_id\': \'00064a80-2b4e-45a6-96f4-bcf60fb925ca\', \'product\': \'[{"lang": "NO", "name": "ALPELISIB ELLER ET FARMASOEYTISK AKSEPTABELT SALT DERAV"}]\', \'filing_date\': \'20201116\', \'maximum_expiry_date\': \'20340908\', \'extension_type\': \'SPC\'}]'}
    
    请生成一个 SQL 查询，以回答用户的问题。返回JSON：{'sql': 'SELECT * FROM table WHERE column = value'}
    """
    # 流式输出示例
    client_stream = LLMClient(model_type="tongyi", model_name="qwq-plus", streaming=True)
    print("流式输出:")
    for chunk in client_stream.invoke(prompt2):
        print(chunk, end="", flush=True)