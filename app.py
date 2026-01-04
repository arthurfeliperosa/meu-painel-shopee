import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard Shopee + Meta", layout="wide")

st.title("📊 Analisador de ROI: Shopee vs Meta Ads")
st.markdown("Suba seus relatórios para cruzar os dados de vendas com os gastos de anúncios.")

col1, col2 = st.columns(2)

with col1:
    shopee_file = st.file_uploader("1. Relatório de Vendas (Shopee)", type=["csv", "xlsx"])
    
with col2:
    meta_file = st.file_uploader("2. Relatório de Gastos (Meta Ads)", type=["csv", "xlsx"])

def process_file(file, label):
    try:
        df = pd.read_csv(file) if "csv" in file.name else pd.read_excel(file)
        
        # Tenta encontrar a coluna de Data automaticamente
        date_col = None
        for col in df.columns:
            if 'Data' in str(col) or 'Time' in str(col) or 'Period' in str(col):
                # Tenta converter para data, se falhar, pula para a próxima
                try:
                    df[col] = pd.to_datetime(df[col])
                    date_col = col
                    break
                except:
                    continue
        
        # Tenta encontrar a coluna de Valor/Gasto automaticamente
        val_col = None
        keywords = ['Total', 'Venda', 'Gasto', 'Amount', 'Spent', 'Preço']
        for col in df.columns:
            if any(key in str(col) for key in keywords):
                val_col = col
                # Limpa símbolos de moeda se houver
                if df[val_col].dtype == 'object':
                    df[val_col] = df[val_col].str.replace('R$', '').str.replace('.', '').str.replace(',', '.').astype(float)
                break
        
        if date_col and val_col:
            df['Data_Ref'] = df[date_col].dt.date
            return df.groupby('Data_Ref')[val_col].sum().reset_index(), val_col
        else:
            st.error(f"Não encontrei colunas de Data ou Valor no arquivo {label}.")
            return None, None
    except Exception as e:
        st.error(f"Erro ao ler {label}: {e}")
        return None, None

if shopee_file and meta_file:
    df_s_daily, col_venda = process_file(shopee_file, "Shopee")
    df_m_daily, col_gasto = process_file(meta_file, "Meta Ads")

    if df_s_daily is not None and df_m_daily is not None:
        # Cruzamento
        df_final = pd.merge(df_s_daily, df_m_daily, left_on='Data_Ref', right_on='Data_Ref', how='outer').fillna(0)
        df_final.columns = ['Data', 'Faturamento_Shopee', 'Gasto_Meta']
        
        # Cálculos
        df_final['Saldo'] = df_final['Faturamento_Shopee'] - df_final['Gasto_Meta']
        df_final['ROAS'] = df_final['Faturamento_Shopee'] / df_final['Gasto_Meta'].replace(0, 1)

        # Métricas
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Faturamento Shopee", f"R$ {df_final['Faturamento_Shopee'].sum():,.2f}")
        m2.metric("Gasto Meta Ads", f"R$ {df_final['Gasto_Meta'].sum():,.2f}")
        m3.metric("Saldo Líquido", f"R$ {df_final['Saldo'].sum():,.2f}")
        m4.metric("ROAS Geral", f"{df_final['Faturamento_Shopee'].sum() / df_final['Gasto_Meta'].sum():.2f}x" if df_final['Gasto_Meta'].sum() > 0 else "0")

        # Gráfico
        fig = px.area(df_final, x='Data', y=['Faturamento_Shopee', 'Gasto_Meta'], 
                      title="Comparativo Diário", barmode='group', color_discrete_sequence=['#2ecc71', '#e74c3c'])
        st.plotly_chart(fig, use_container_width=True)

        # Tabela
        st.dataframe(df_final.sort_values('Data', ascending=False), use_container_width=True)
