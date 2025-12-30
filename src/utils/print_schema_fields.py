import json
import sys

# 设置默认文件路径
DEFAULT_FILE = '/Users/wangwei/IdeaProjects/galaxy-qgw-service/config/tsg/sr/schema/traffic_channel_metric.json'

# 从命令行参数获取文件路径，如果没有则使用默认值
file_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_FILE
print(file_path)
print("─" * 50)

try:
    # 读取JSON文件
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 提取所有name值
    names = [field['name'] for field in data['fields']]
    
    # 用逗号分隔打印一行
    print(', '.join(names))
    print("─" * 50)

    # 统计字段数量
    print(f"总字段数: {len(names)}")

except FileNotFoundError:
    print(f"错误: 文件 '{file_path}' 不存在")
except json.JSONDecodeError:
    print(f"错误: 文件 '{file_path}' 不是有效的JSON格式")
except Exception as e:
    print(f"错误: {str(e)}")