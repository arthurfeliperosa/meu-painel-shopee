import streamlit as st
import pandas as pd
import plotly.express as px

# Configuração da página
st.set_page_config(page_title="Dashboard Shopee + Meta", layout="wide")

st.title("📊 Analisador de ROI: Shopee vs Meta Ads")
st.markdown("Suba seus relatórios para cruzar os dados de vendas com os gastos de anúncios.")

# Layout de Colunas para Upload
col1, col2 = st.columns(2)

with col1:
    shopee_file = st.file_uploader("1. Relatório de Vendas (Shopee)", type=["csv", "xlsx"])
    
with col2:
    meta_file = st.file_uploader("2. Relatório de Gastos (Meta Ads)", type=["csv", "xlsx"])

if shopee_file and meta_file:
    # --- PROCESSAMENTO SHOPEE ---
    # Lendo o arquivo (ajuste o encoding se necessário para CSVs brasileiros)
    try:
        df_shopee = pd.read_csv(shopee_file) if "csv" in shopee_file.name else pd.read_excel(shopee_file)
        
        # Tentativa de identificar a coluna de data e valor (Shopee muda nomes as vezes)
        # Ajuste esses nomes conforme o seu relatório real
        df_shopee['Data'] = pd.to_datetime(df_shopee.iloc[:, 0]).dt.date # Geralmente a 1ª coluna é data
        faturamento_col = [col for col in df_shopee.columns if 'Total' in col or 'Venda' in col][0]
        df_shopee_daily = df_shopee.groupby('Data')[faturamento_col].sum().reset_index()
    except Exception as e:
        st.error(f"Erro ao ler planilha Shopee: {e}")

    # --- PROCESSAMENTO META ADS ---
    try:
        df_meta = pd.read_csv(meta_file) if "csv" in meta_file.name else pd.read_excel(meta_file)
        
        # Ajuste para identificar data e valor gasto no Meta
        df_meta['Data'] = pd.to_datetime(df_meta.iloc[:, 0]).dt.date
        gasto_col = [col for col in df_meta.columns if 'Gasto' in col or 'Valor' in col or 'Amount' in col][0]
        df_meta_daily = df_meta.groupby('Data')[gasto_col].sum().reset_index()
    except Exception as e:
        st.error(f"Erro ao ler planilha Meta: {e}")

    # --- CRUZAMENTO DOS DADOS ---
    if 'df_shopee_daily' in locals() and 'df_meta_daily' in locals():
        df_final = pd.merge(df_shopee_daily, df_meta_daily, on='Data', how='outer').fillna(0)
        
        # Cálculos Principais
        df_final['Resultado'] = df_final[faturamento_col] - df_final[gasto_col]
        df_final['ROAS'] = df_final[faturamento_col] / df_final[gasto_col].replace(0, 1)

        # --- EXIBIÇÃO ---
        total_faturado = df_final[faturamento_col].sum()
        total_gasto = df_final[gasto_col].sum()
        roas_geral = total_faturado / total_gasto if total_gasto > 0 else 0

        # Métricas em Destaque
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Faturamento Total", f"R$ {total_faturado:,.2f}")
        m2.metric("Gasto Meta Ads", f"R$ {total_gasto:,.2f}")
        m3.metric("Saldo (Fat - Gasto)", f"R$ {(total_faturado - total_gasto):,.2f}")
        m4.metric("ROAS Geral", f"{roas_geral:.2f}x")

        # Gráfico de comparação
        st.subheader("Desempenho Diário")
        fig = px.line(df_final, x='Data', y=[faturamento_col, gasto_col], 
                      labels={'value': 'Valor (R$)', 'variable': 'Métrica'},
                      title="Vendas Shopee vs Gastos Meta")
        st.plotly_chart(fig, use_container_width=True)

        # Tabela Detalhada
        st.subheader("Dados Cruzados")
        st.dataframe(df_final.sort_values('Data', ascending=False), use_container_width=True)
else:
    st.info("Aguardando o upload de ambas as planilhas para gerar o cruzamento.")