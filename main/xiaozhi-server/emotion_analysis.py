import pandas as pd
import re
from snownlp import SnowNLP
import matplotlib.pyplot as plt
import logging

def clean_text(text):
    """清理文本数据"""
    if pd.isna(text):
        return ""
    
    text = str(text)
    
    # 去除各种特殊格式
    text = re.sub(r'【.*?】', '', text)  # 去除【】格式
    text = re.sub(r'//.*?:', '', text)  # 去除转发格式
    text = re.sub(r'L.*?微博视频', '', text)  # 去除视频链接
    text = re.sub(r'O.*?网页链接', '', text)  # 去除网页链接
    
    return text.strip()

def split_sentences(text):
    """将文本分割成句子"""
    sentences = re.split(r'[，。.！？，:；—+（）：」「#【】.…\n]+', text)
    return [s.strip() for s in sentences if s.strip()]

def sentiment_analysis(text):
    """进行情感分析"""
    s = SnowNLP(text)
    return s.sentiments

def sentiment_label(sentiment):
    """将情感值转换为标签"""
    if sentiment < 0.33:
        return '消极'
    elif sentiment > 0.67:
        return '积极'
    else:
        return '中性'

def numerical_label(tendency):
    """将情感倾向转换为数值标签"""
    if tendency == '消极':
        return -1
    elif tendency == '积极':
        return 1
    else:
        return 0

def analyze_single_sentence(text):
    """分析单句情感"""
    # 清理文本
    cleaned_text = clean_text(text)
    
    # 情感分析
    sentiment_value = sentiment_analysis(cleaned_text)
    sentiment_category = sentiment_label(sentiment_value)
    numerical_value = numerical_label(sentiment_category)
    
    return {
        'text': cleaned_text,
        'sentiment_value': sentiment_value,
        'sentiment_category': sentiment_category,
        'numerical_value': numerical_value
    }

def process_data(input_file, output_dir):
    """处理数据的主函数"""
    # 读取Excel文件
    df = pd.read_excel(input_file)
    
    if '博文内容' not in df.columns:
        print("Excel 文件中未找到 '博文内容' 列！")
        return
    
    # 清理文本
    df['博文内容'] = df['博文内容'].apply(clean_text)
    
    # 去除空值和重复值
    df_cleaned = df.dropna(subset=['博文内容'])
    df_cleaned = df_cleaned.drop_duplicates(subset=['博文内容'])
    
    # 保存清理后的数据
    cleaned_file = f"{output_dir}/cleaned_data.xlsx"
    df_cleaned.to_excel(cleaned_file, index=False)
    print(f"清理后的数据已保存至 {cleaned_file}")
    
    # 情感分析
    df_cleaned['博文内容'] = df_cleaned['博文内容'].astype(str)
    df_cleaned['分句'] = df_cleaned['博文内容'].apply(lambda text: str(split_sentences(text)))
    df_cleaned['情感分析'] = df_cleaned['博文内容'].apply(lambda text: [sentiment_analysis(sentence) for sentence in split_sentences(text)])
    df_cleaned['整句情感分析'] = df_cleaned['情感分析'].apply(lambda sentiments: sum(sentiments) / len(sentiments) if sentiments else 0.5)
    df_cleaned['情感标签'] = df_cleaned['情感分析'].apply(lambda sentiments: [sentiment_label(s) for s in sentiments])
    df_cleaned['情感倾向'] = df_cleaned['整句情感分析'].apply(lambda sentiment: sentiment_label(sentiment))
    df_cleaned['情感数值标签'] = df_cleaned['情感倾向'].apply(numerical_label)
    
    # 保存情感分析结果
    result_file = f"{output_dir}/sentiment_analysis_result.xlsx"
    df_cleaned.to_excel(result_file, index=False)
    print(f"情感分析结果已保存至 {result_file}")
    
    return df_cleaned

def plot_results(df, output_dir):
    """绘制可视化图表"""
    # 设置中文字体
    plt.rcParams['font.sans-serif'] = ['SimSun']
    plt.rcParams['axes.unicode_minus'] = False
    
    # 绘制情感倾向圆环图
    sentiment_counts = df['情感倾向'].value_counts()
    colors = ['#ffcc00', '#ff6347', '#1f77b4']
    
    plt.figure(figsize=(8, 6))
    plt.pie(sentiment_counts, 
            labels=sentiment_counts.index, 
            autopct='%1.1f%%', 
            startangle=90, 
            wedgeprops={'width': 0.3}, 
            colors=colors)
    plt.title('情感倾向分布')
    plt.legend(sentiment_counts.index, loc='upper right', bbox_to_anchor=(1.2, 1))
    plt.savefig(f"{output_dir}/sentiment_distribution.png", dpi=300)
    plt.close()
    
    # 绘制情感值分布直方图
    plt.figure(figsize=(8, 6))
    plt.hist(df['整句情感分析'], bins=10, range=(0, 1), color='skyblue', edgecolor='black')
    plt.title('情感值分布图', fontsize=14)
    plt.xlabel('情感值', fontsize=12)
    plt.ylabel('条数', fontsize=12)
    plt.savefig(f"{output_dir}/sentiment_value_distribution.png", dpi=300)
    plt.close()

def main():
    # 设置输入输出路径
    input_file = r'C:\Users\Administrator\Desktop\20250307阿迪达斯情感分析\Adidas2022--情感分析用.xlsx'
    output_dir = r'C:\Users\Administrator\Desktop\20250307阿迪达斯情感分析'
    
    # 处理数据
    df = process_data(input_file, output_dir)
    
    # 绘制图表
    plot_results(df, output_dir)
    
    print("处理完成！")

if __name__ == "__main__":
    main() 