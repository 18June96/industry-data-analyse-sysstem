#streamlit run 03谢卓君.py
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import streamlit as st

# 全局设置
plt.rcParams['font.sans-serif'] = 'SimHei'  # 解决中文显示
plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示

def st_data(nm, info):
    """获取行业数据并绘制图表"""
    data = pd.read_csv('index_trdata.csv')
    trdata = pd.read_csv('stk_trdata.csv')
    findata = pd.read_csv('fin_data.csv')
    co_data = pd.read_excel('上市公司基本信息.xlsx')

    #筛选指定行业的行业指数交易数据（大于600条）
    data_i = data[data['name'] == nm].sort_values('trade_date')
    data_i.columns = ['指数代码', '行业名称', '交易日期', '开盘指数', '收盘指数', '成交量', '市盈率', '市净率']
    if len(data_i) <= 600:
        st.warning(f"【{nm}】行业指数数据不足600条（当前{len(data_i)}条）")
        return None

    #绘制行业收盘指数走势图
    f1, ax = plt.subplots(figsize=(8, 4))
    ax.plot(range(len(data_i)), data_i['收盘指数'], color='#1f77b4')
    ax.set_title(f'申万{nm}行业指数走势图', fontsize=12, pad=10)
    ax.set_xticks([0, 100, 200, 300, 400, 500, 600])
    ax.set_xticklabels(data_i['交易日期'].iloc[[0, 100, 200, 300, 400, 500, 600]], rotation=45)
    ax.grid(alpha=0.3)

    # 筛选条件保留列名（新版一级行业、交易所），取数用位置索引
    info_filtered = info[(info['新版一级行业'] == nm) & (info['交易所'] == 'A股')]
    chy_code = info_filtered.iloc[:, [2, 3]]  # 按位置取第3、4列（索引从0开始）
    chy_code.columns = ['ts_code', 'nm']  # 统一列名，方便后续合并

    # 合并数据
    co_data = pd.merge(co_data, chy_code, how='inner', on='ts_code')
    trdata_hy = pd.merge(trdata, chy_code, how='inner', on='ts_code')
    trdata_hy = trdata_hy.sort_values(['ts_code', 'trade_date'])
    trdata_hy.columns = ['股票代码', '交易日期', '收盘价', '成交量', '成交金额', '股票简称']

    #绘制6只股票的走势图（交易记录>600条）
    f2, axs = plt.subplots(3, 2, figsize=(12, 8))
    axs = axs.flatten()  # 扁平化子图数组
    code_list = trdata_hy['股票代码'].unique()
    p = 0  # 计数

    for code in code_list:
        trdata_k = trdata_hy[trdata_hy['股票代码'] == code]
        if len(trdata_k) > 600 and p < 6:
            axs[p].plot(range(len(trdata_k)), trdata_k['收盘价'], color='#ff7f0e')
            axs[p].set_title(trdata_k['股票简称'].iloc[0], fontsize=10)
            axs[p].set_xticks([0, 100, 200, 300, 400, 500, 600])
            axs[p].set_xticklabels(trdata_k['交易日期'].iloc[[0, 100, 200, 300, 400, 500, 600]], rotation=45)
            axs[p].grid(alpha=0.2)
            p += 1

    #隐藏多余的子图
    while p < 6:
        axs[p].set_visible(False)
        p += 1
    plt.tight_layout()

    #整理财务数据
    code_p = pd.DataFrame({'股票代码': code_list})
    findata_m = pd.merge(findata, code_p, how='inner', on='股票代码')

    return (f1, f2, data_i, findata_m, trdata_hy, co_data.iloc[:, :-1])


def Fr(data, year):
    """综合评价函数"""
    if data.empty:
        return pd.DataFrame(columns=['股票代码', '股票简称', '综合得分'])
    
    tdata = data[data['年度'] == year]
    if tdata.empty:
        st.warning(f"无{year}年度财务数据")
        return pd.DataFrame(columns=['股票代码', '股票简称', '综合得分'])

    # 1.空值和负值处理
    data_x = tdata.iloc[:, 1:-1]
    data_x = data_x[data_x > 0]  # 过滤负值
    data_x['股票代码'] = tdata['股票代码'].values
    data_x = data_x.dropna()  # 删除空值

    if data_x.empty:
        return pd.DataFrame(columns=['股票代码', '股票简称', '综合得分'])

    # 2.标准化
    X = data_x.iloc[:, :-1]
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # 3.主成分分析
    pca = PCA(n_components=0.95)
    Y = pca.fit_transform(X_scaled)
    gxl = pca.explained_variance_ratio_

    # 4.综合得分
    F = (Y * gxl).sum(axis=1)

    # 合并股票简称
    try:
    # 读取Excel，列名用实际的ts_code和name
        stk_data = pd.read_excel('股票基本信息表.xlsx')[['ts_code', 'name']]
        # 把列名改成代码里需要的“股票代码”“股票简称”（方便后续合并）
        stk_data.columns = ['股票代码', '股票简称']
        # 后续合并逻辑不变
        nm_stk_data = pd.merge(stk_data, data_x[['股票代码']], on='股票代码')
        nm_stk_data['综合得分'] = F
        nm_stk_data = nm_stk_data.sort_values('综合得分', ascending=False).reset_index(drop=True)
    except:
        nm_stk_data = pd.DataFrame({
            '股票代码': data_x['ts_code'].values,
            '股票简称': '',
            '综合得分': F
        }).sort_values('综合得分', ascending=False).reset_index(drop=True)

    return nm_stk_data

def Tr(rdata, rank, date1, date2):
    A1 = pd.read_csv('复权交易数据2023.csv')
    A2 = pd.read_csv('复权交易数据2024.csv')
    A3 = pd.read_csv('复权交易数据2025.csv')
    A = pd.concat([A1, A2, A3])
    A['trade_date'] = A['trade_date'].astype(str)
    date1_str = date1.strftime('%Y%m%d')
    date2_str = date2.strftime('%Y%m%d')

    top_stk = rdata.head(rank)['股票代码'].tolist()
    stock_ret_list = []  # 存储单只股票的收益率
    r = 0.0

    for code in top_stk:
        stk_data = A[
            (A['ts_code'] == code) & 
            (A['trade_date'] >= date1_str) & 
            (A['trade_date'] <= date2_str)
        ].sort_values('trade_date')
        
        if len(stk_data) >= 2:
            p1 = stk_data['close'].iloc[0]
            p2 = stk_data['close'].iloc[-1]
            ri = (p2 - p1) / p1
            r += ri
            # 把股票代码、收益率存入列表
            stock_ret_list.append({'股票代码': code, '单只收益率': f"{ri*100:.2f}%"})
        else:
            stock_ret_list.append({'股票代码': code, '单只收益率': "数据不足"})

    # 构建单只股票收益率的DataFrame
    stock_ret_df = pd.DataFrame(stock_ret_list)

    # 计算沪深300收益率
    rv = 0.0
    hs300 = pd.read_excel('沪深300指数交易数据.xlsx')
    hs300['trade_date'] = hs300['trade_date'].astype(str)
    hs300_data = hs300[
            (hs300['trade_date'] >= date1_str) & 
            (hs300['trade_date'] <= date2_str)
    ].sort_values('trade_date')
        
    if len(hs300_data) >= 2:
        rv = (hs300_data['close'].iloc[-1] - hs300_data['close'].iloc[0]) / hs300_data['close'].iloc[0]

    return stock_ret_df, round(r, 4), round(rv, 4)  # 返回：单只收益率DataFrame、总收益率、沪深300收益率


def st_fig():
    # 页面设置
    st.set_page_config(
        page_title="申万行业数据分析",
        layout='wide',
        initial_sidebar_state='expanded'
    )

    # 侧边栏
    with st.sidebar:
        st.title("申万行业分析")
        st.divider()

        # 读取行业分类表
        try:
            info = pd.read_excel('最新个股申万行业分类(完整版-截至7月末).xlsx')
            nm_L = sorted(info['新版一级行业'].unique())
        except:
            st.error("行业分类表读取失败！请检查文件路径和名称")
            return

        # 行业选择
        nm = st.selectbox("选择行业", nm_L, index=0)
        st.divider()

        # 评价参数
        st.subheader("评价参数")
        year = st.selectbox("评价年度", [2022,2023, 2024], index=1)
        rank = st.selectbox("投资组合数量", [5, 10, 15, 20], index=0)
        st.divider()

        # 持有期选择
        st.subheader("持有期")
        date1 = st.date_input("开始日期", value=pd.to_datetime('2023-01-01'))
        date2 = st.date_input("结束日期", value=pd.to_datetime('2023-12-31'))

    # 主内容区
    st.header(f"申万{nm}行业数据分析", divider='blue')

    # 调用数据处理函数
    result = st_data(nm, info)
    if not result:
        return
    f1, f2, data_i, findata_m, trdata_hy, co_data = result

    #图表展示
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("指数走势图")
        st.pyplot(f1)
    with col2:
        st.subheader("前6只股票价格走势图")
        st.pyplot(f2)

    st.divider()

    # 数据表格-折叠展示
    with st.expander("指数交易数据", expanded=False):
        st.dataframe(data_i, use_container_width=True, height=300)

    with st.expander("上市公司基本信息", expanded=False):
        st.dataframe(co_data, use_container_width=True, height=300)

    with st.expander("股票财务数据", expanded=False):
        st.dataframe(findata_m, use_container_width=True, height=300)

    with st.expander("股票交易数据（前2000条）", expanded=False):
        st.dataframe(trdata_hy.iloc[:2000], use_container_width=True, height=300)

    st.divider()

    st.subheader("综合评价结果")
    eval_result = Fr(findata_m, year)
    if eval_result.empty:
        st.dataframe(pd.DataFrame({'股票代码': [], '股票简称': [], '综合得分': []}), use_container_width=True)
    else:
        st.dataframe(eval_result, use_container_width=True, height=300)
    
        st.divider()  # 分割线
        #画折线图
        st.subheader(f"前{rank}只股票综合得分折线图")
        # 提取前rank个股票的数据（rank是侧边栏选择的投资组合数量）
        top_rank_data = eval_result.head(rank)
        # 绘制折线图
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(top_rank_data['股票简称'], top_rank_data['综合得分'], marker='o', color='#2ca02c', linewidth=2)
        # 添加数据标签
        for i, score in enumerate(top_rank_data['综合得分']):
            ax.text(i, score + 0.1, f"{score:.2f}", ha='center')
        # 设置图表样式
        ax.set_title(f"前{rank}只股票综合得分分布", fontsize=12)
        ax.set_xlabel("股票简称",fontsize=9, fontweight='normal')
        ax.set_ylabel("综合得分",fontsize=9, fontweight='normal')
        ax.tick_params(axis='x', rotation=45)  # 旋转x轴标签避免重叠
        ax.grid(alpha=0.3)
        # 在Streamlit中展示图表
        plt.tight_layout()  # 自动调整布局
        st.pyplot(fig)
    
    st.divider()

    st.subheader("收益率分析")
    if not eval_result.empty:
        # 调用Tr函数，获取单只收益率DataFrame、总收益率、沪深300收益率
        stock_ret_df, r, rv = Tr(eval_result, rank, date1, date2)
    
        #展示单只股票收益率的数据框
        st.write("单只股票收益率：")
        st.dataframe(stock_ret_df, use_container_width=True)  
        
        #单独展示沪深300收益率和投资组合总收益率
        col1, col2 = st.columns(2)
        with col1:
            st.metric("投资组合总收益率", f"{r*100:.2f}%")
        with col2:
            st.metric("沪深300同期收益率", f"{rv*100:.2f}%")
    else:
        st.write("暂无有效数据计算收益率")

if __name__ == "__main__":
    st_fig()