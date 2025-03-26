from celery import shared_task
from .models import FileUploadTask
from utils.logger_manager import get_logger
from .milvus_helper import process_singel_file
from ..knowledge.vector_store import MilvusVectorStore
from ..knowledge.embedding import BGEM3Embedder
from django.conf import settings
import gc
import os
import hashlib
from datetime import datetime


logger = get_logger(__name__)

# 在文件开头预加载模型
try:
    global_embedder = BGEM3Embedder(model_name="BAAI/bge-m3", device='cpu')
    logger.info("全局 embedder 实例创建成功")
except Exception as e:
    logger.error(f"全局 embedder 实例创建失败: {str(e)}")
    global_embedder = None

@shared_task(
    bind=True,
    ignore_result=False,  # 不忽略结果
    time_limit=3600,      # 1小时超时
    soft_time_limit=3300  # 55分钟软超时
)
def process_file_upload(self, task_id: int):
    """异步处理文件上传任务"""
    logger.info(f"开始处理上传任务: {task_id}")
    
    try:
        task = FileUploadTask.objects.get(id=task_id)
        logger.info(f"获取到任务: {task.file_name}")
        
        # 检查必要的属性
        if not hasattr(task, 'file_path'):
            raise ValueError("任务缺少 file_path 属性")
        if not hasattr(task, 'file_name'):
            raise ValueError("任务缺少 file_name 属性")
        
        # 使用全局 embedder 实例
        if global_embedder is None:
            raise ValueError("全局 embedder 实例未初始化")
        
        # 创建 vector_store 实例
        vector_store = MilvusVectorStore(
            host=settings.VECTOR_DB_CONFIG['host'],
            port=settings.VECTOR_DB_CONFIG['port'],
            collection_name=settings.VECTOR_DB_CONFIG['collection_name']
        )
        
        # 更新状态为处理中
        task.status = 'processing'
        task.save()
        logger.info(f"更新任务状态为处理中: {task_id}")
        
        # 设置环境变量
        os.environ['CUDA_VISIBLE_DEVICES'] = ''
        os.environ['PYTORCH_ENABLE_MPS_FALLBACK'] = '0'
        
        logger.info("准备创建 embedder 实例...")
        local_embedder = BGEM3Embedder(
                model_name="BAAI/bge-m3",
                # device='cpu'  # 强制使用 CPU
            )
        logger.info("embedder 实例创建成功")
        chunks = process_singel_file(task.file_path)
        if not chunks:
            logger.info("文件中无有效内容")
            task.status = 'completed'
            task.save()
            logger.info(f"文件 {task.file_name} 处理完成")
            return {'status': 'success', 'task_id': task_id} 
         # 提取所有chunk.text并记录日志
        if isinstance(chunks, list):
            # 直接从chunks中提取text属性
            text_contents = []
            for i, chunk in enumerate(chunks):
                if hasattr(chunk, 'text'):
                    text_contents.append(str(chunk.text))
                else:
                    text_contents.append(str(chunk))
        
            logger.info(f"共提取了 {len(text_contents)} 个文本内容")
        else:
            # 单一文本块的情况
            if hasattr(chunks, 'text'):
                text_contents = [str(chunks.text)]
            else:
                text_contents = [str(chunks)]
            logger.info(f"提取了单个文本内容: {text_contents[0][:100]}...")
        # 直接生成所有文本内容的向量
        logger.info("开始生成向量")
        start_time = datetime.now()
        try:
            # 直接为所有文本内容生成向量
            all_embeddings = local_embedder.get_embeddings(texts=text_contents, show_progress_bar=False)
            logger.info(f"成功生成 {len(all_embeddings)} 个向量")
            
            # 确保embeddings是列表格式
            embeddings_list = []
            for emb in all_embeddings:
                if hasattr(emb, 'tolist'):
                    emb = emb.tolist()
                embeddings_list.append(emb)
            
            # 准备插入数据
            data_to_insert = []
            file_type = task.file_name.split('.')[-1] if '.' in task.file_name else 'unknown'
            
            for i in range(len(text_contents)):
                try:
                    item = {
                        "embedding": embeddings_list[i],
                        "content": text_contents[i],
                        "metadata": '{}',
                        "source": str(task.file_path),  # 确保是字符串
                        "doc_type": file_type,
                        "chunk_id": f"{hashlib.md5(os.path.basename(task.file_name).encode()).hexdigest()[:10]}_{i:04d}",
                        "upload_time": datetime.now().isoformat()
                    }
                    data_to_insert.append(item)
                except Exception as e:
                    logger.error(f"构建第 {i} 条数据时出错: {str(e)}", exc_info=True)
                    raise
            
            # 插入数据到Milvus
            logger.info(f"开始往milvus中插入 {len(data_to_insert)} 条数据")
            vector_store.add_data(data_to_insert)
            logger.info("数据插入完成")
            
            total_time = (datetime.now() - start_time).total_seconds()
            logger.info(f"向量生成和插入完成，总耗时: {total_time:.2f} 秒")
        except Exception as e:
            logger.error(f"生成或插入向量时出错: {str(e)}", exc_info=True)
                    
        

        # try:
        #     # 创建 embedder 实例
        #     local_embedder = BGEM3Embedder(
        #         model_name="BAAI/bge-m3",
        #         device='cpu'  # 强制使用 CPU
        #     )
        #     logger.info("embedder 实例创建成功")
            
        #     # 测试 embedder
        #     test_result = local_embedder.get_embeddings(["测试文本"])
        #     logger.info(f"embedder 测试成功，向量维度: {len(test_result[0])}")
            
        # except Exception as embed_init_error:
        #     logger.error(f"创建 embedder 实例失败: {str(embed_init_error)}", exc_info=True)
        #     task.status = 'failed'
        #     task.error_message = f"创建 embedder 实例失败: {str(embed_init_error)}"
        #     task.save()
        #     raise
        
        # # 处理文件获取文本块
        # chunks = process_singel_file(task.file_path)
        # if not chunks:
        #     logger.error(f"文件中未提取到有效内容: {task.file_path}")
        #     raise ValueError("文件中未提取到有效内容")
            
        # # 更新总块数
        # task.total_chunks = len(chunks)
        # task.save()
        # logger.info(f"文件总块数: {len(chunks)}")
        
        # # 处理每个文本块
        # for i, chunk in enumerate(chunks, 1):
        #     try:
        #         logger.info(f"处理第 {i}/{len(chunks)} 块")
        #         # 获取文本内容
        #         if hasattr(chunk, 'text'):
        #             text_content = str(chunk.text)
        #         else:
        #             text_content = str(chunk)
                
        #         # 生成向量
        #         embedding = local_embedder.get_embeddings([text_content])[0]
                
        #         # 准备数据
        #         data = {
        #             "embedding": embedding.tolist(),
        #             "content": text_content,
        #             "metadata": '{}',
        #             "source": task.file_path,
        #             "doc_type": task.file_name.split('.')[-1],
        #             "chunk_id": f"{task.id}_{i:04d}",
        #             "upload_time": task.created_at.isoformat()
        #         }
                
        #         # 存储向量
        #         vector_store.add_data([data])
                
        #         # 更新进度
        #         task.processed_chunks = i
        #         task.save()
        #         logger.info(f"已处理 {i}/{len(chunks)} 块")
                
        #         # 手动清理内存
        #         del embedding
        #         gc.collect()
                
        #     except Exception as chunk_error:
        #         logger.error(f"处理第 {i} 块时出错: {str(chunk_error)}", exc_info=True)
        #         continue
            
        # 更新状态为完成
        task.status = 'completed'
        task.save()
        logger.info(f"文件 {task.file_name} 处理完成")
        
    except Exception as e:
        logger.error(f"处理文件失败: {str(e)}", exc_info=True)
        if 'task' in locals():
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
        raise
    finally:
        # 清理资源
        if 'local_embedder' in locals():
            del local_embedder
        if 'vector_store' in locals():
            del vector_store
        gc.collect()
        logger.info("清理资源完成")

    return {'status': 'success', 'task_id': task_id} 