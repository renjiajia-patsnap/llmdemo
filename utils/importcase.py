import pandas as pd
import json
import os

# 读取 Excel 文件（替换为您的文件路径）
excel_file = r'D:\cases\Metersphere_case_Analytics.xlsx'

# 检查文件是否存在
if not os.path.exists(excel_file):
    raise FileNotFoundError(f"Excel 文件未找到: {excel_file}")

# 读取 Excel 数据
try:
    data = pd.read_excel(excel_file)
except Exception as e:
    raise Exception(f"读取 Excel 文件失败: {e}")

# 处理合并单元格：将 NaN 值填充为前一个非空值
data['ID'] = data['ID'].ffill()
data['用例名称'] = data['用例名称'].ffill()
data['所属模块'] = data['所属模块'].ffill()
data['责任人'] = data['责任人'].ffill()
data['用例等级'] = data['用例等级'].ffill()

# 优先级映射
priority_map = {'P0': 0, 'P1': 1, 'P2': 2}

# 用于存储所有 JSON 对象的列表
json_cases = []

# 按 ID 分组
for case_id, group in data.groupby('ID'):
    case_name = f"{group['用例名称'].iloc[0]}_{case_id}"
    module = group['所属模块'].iloc[0]
    priority = priority_map.get(group['用例等级'].iloc[0], 1)
    remark = f"责任人: {group['责任人'].iloc[0]}" if pd.notna(group['责任人'].iloc[0]) else ""

    # 构建 steps 列表
    steps = []
    for index, row in group.iterrows():
        step_desc = str(row['步骤描述']) if pd.notna(row['步骤描述']) else ''
        expect_desc = str(row['预期结果']) if pd.notna(row['预期结果']) else ''
        if step_desc or expect_desc:  # 过滤掉空行
            steps.append({
                "step": step_desc.strip(),
                "expect": expect_desc.strip(),
                "_X_ROW_KEY": f"row_{index}"
            })

    # 构建 JSON 对象
    json_case = {
        "product": "958cb35254ff4fd6a9277d77c74e88c8",
        "verification_method": "MANUAL",
        "case_type": "FUNCTION",
        "module": module,
        "client": "WEB",
        "priority": priority,
        "env": ["8c94587c937b48e49a9d09ecb88207f2"],
        "remark": remark,
        "case_name": case_name,
        "steps": steps
    }

    json_cases.append(json_case)

# 将结果保存为 JSON 文件
output_file = r'C:\Users\renjiajia\PycharmProjects\llmdemo\cases_output.json'
try:
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(json_cases, f, ensure_ascii=False, indent=2)
    print(f"JSON 文件已生成：{output_file}")
except Exception as e:
    print(f"保存 JSON 文件失败: {e}")