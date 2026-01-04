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

def limpar_valor(df, coluna):
    """Converte valores com R$, pontos e vírgulas para números reais"""
    if df[coluna].dtype == 'object':
        return df[coluna].astype(str).str.replace('R$', '', regex=False)\
                         .str.replace('.', '', regex=False)\
                         .str.replace(',', '.', regex=False)\
                         .str.strip().astype(float)
    return df[coluna].astype(float)

def processar_dados(file, tipo):
    try:
        df = pd.read_csv(file) if "csv" in file.name else pd.read_excel(file)
        
        # Identificar coluna de Data
        col_data = None
        for c in df.columns:
            # Verifica se o nome da coluna sugere data ou tempo
            if any(palavra in str(c).lower() for palavra in ['data', 'time', 'date', 'período', 'dia']):
                # Tenta converter os valores da coluna para data
                try:
                    df[c] = pd.to_datetime(df[c])
                    col_data = c
                    break
                except: continue
        
        # Identificar coluna de Valor
        col_valor = None
        # Palavras chave para Shopee (Venda/Comissão) ou Meta (Gasto/Amount)
        keywords = ['total', 'venda', 'comissão', 'gasto', 'spent', 'amount', 'valor', 'price']
        for c in df.columns:
            if any(k in str(c).lower() for k in keywords):
                try:
                    df[c] = limpar_valor(df, c)
                    col_valor = c
                    break
                except: continue

        if col_data and col_valor:
            df['Data_Ref'] = df[col_data].dt.date
            resumo = df.groupby('Data_Ref')[col_valor].sum().reset_index()
            return resumo, col_valor
        else:
            st.error(f"Não achei colunas de Data/Valor no arquivo {tipo}. Verifique os títulos das colunas.")
            return None, None
    except Exception as e:
        st.error(f"Erro no processamento ({tipo}): {e}")
        return None, None

if shopee_file and meta_file:
    df_s, nome_col_s = processar_dados(shopee_file, "Shopee")
    df_m, nome_col_m = processar_dados(meta_file, "Meta Ads")

    if df_s is not None and df_m is not None:
        # Cruza as duas tabelas pela Data
        df_final = pd.merge(df_s, df_m, on='Data_Ref', how='outer').fillna(0)
        df_final.columns = ['Data', 'Receita_Shopee', 'Custo_Meta']
        
        # Métricas simples
        df_final['Lucro_Bruto'] = df_final['Receita_Shopee'] - df_final['Custo_Meta']
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Receita Shopee", f"R$ {df_final['Receita_Shopee'].sum():,.2f}")
        m2.metric("Gasto Meta", f"R$ {df_final['Custo_Meta'].sum():,.2f}")
        m3.metric("Saldo Final", f"R$ {df_final['Lucro_Bruto'].sum():,.2f}")

        st.subheader("Gráfico de Performance Diária")
        fig = px.line(df_final, x='Data', y=['Receita_Shopee', 'Custo_Meta'], 
                      color_discrete_map={"Receita_Shopee": "#2ecc71", "Custo_Meta": "#e74c3c"})
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("Tabela de Dados Cruzados")
        st.dataframe(df_final.sort_values('Data', ascending=False), use_container_width=True)
