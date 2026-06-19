"""文件路径常量"""
import os
from pathlib import Path

# 项目根目录
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 文件保存目录
FILE_SAVE_DIR = os.path.join(PROJECT_ROOT, "tmp", "file")

# 知识库文档目录
DOCUMENTS_DIR = os.path.join(PROJECT_ROOT, "documents")
