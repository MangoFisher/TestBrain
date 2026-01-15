import pypandoc

def word_to_markdown(input_file, output_file):
    '''
    将Word文档转换为Markdown格式
    '''
    try:
        # 调用 pypandoc 进行转换
        output = pypandoc.convert_file(input_file, 'markdown', outputfile=output_file)
        if output == '':
            print(f"成功将 {input_file} 转换为 {output_file}")
        else:
            print("转换过程中出现问题:", output)
    except Exception as e:
        print(f"转换失败: {e}")


