import streamlit as st
import pandas as pd
import plotly.express as px

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="Dashboard ROI - Shopee & Meta",
    page_icon="🚀",
    layout="wide"
)

# --- CSS CUSTOMIZADO ---
st.markdown("""
    <style>
    .stApp {
        background-color: #0e1117;
    }
    div[data-testid="stMetric"] {
        background-color: #1f2937;
        border: 1px solid #374151;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    div[data-testid="stMetricLabel"] {
        color: #9ca3af;
        font-size: 14px;
    }
    div[data-testid="stMetricValue"] {
        color: #f3f4f6;
        font-size: 28px;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Analisador de Lucro: Shopee vs Ads")
st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📂 Importar Dados")
    shopee_file = st.file_uploader("Relatório Shopee", type=["csv", "xlsx"])
    meta_file = st.file_uploader("Relatório Meta Ads", type=["csv", "xlsx"])
    st.info("💡 Dica: O sistema ignora automaticamente colunas vazias ou de ID.")

# --- FUNÇÕES DE LIMPEZA E LÓGICA ---
def limpar_moeda(valor):
    if isinstance(valor, (int, float)):
        return valor
    valor = str(valor).lower()
    valor = valor.replace('r$', '').replace('brl', '').replace('usd', '')
    valor = valor.replace('.', '').replace(',', '.') 
    try:
        return float(valor.strip())
    except:
        return 0.0

def encontrar_coluna_data(df):
    """
    Lógica 'Blindada' V2: 
    Verifica se a coluna tem dados ANTES de tentar ler a primeira linha.
    """
    # 1. Tentar pelo nome da coluna (Prioridade Alta)
    colunas_data_keywords = ['data', 'date', 'time', 'dia', 'period', 'created_at', 'purchase_time']
    for col in df.columns:
        if any(k in str(col).lower() for k in colunas_data_keywords):
            try:
                # CORREÇÃO AQUI: Verifica se há dados válidos antes de acessar
                series_validas = df[col].dropna()
                if series_validas.empty:
                    continue # Pula se a coluna estiver toda vazia
                
                sample = series_validas.iloc[0]
                pd.to_datetime(sample, dayfirst=True) 
                return col
            except:
                continue
    
    # 2. Varredura de conteúdo (Se o nome falhar)
    for col in df.columns:
        # Pega apenas linhas não vazias
        series_validas = df[col].dropna()
        if series_validas.empty:
            continue

        sample = str(series_validas.iloc[0])
        
        # Ignorar colunas que parecem IDs (muito longas ou sem separadores)
        if len(sample) > 18: 
            continue
        if not any(c in sample for c in ['/', '-', ':']): 
            continue
            
        try:
            pd.to_datetime(df[col], errors='raise') 
            return col
        except:
            continue
    return None

def encontrar_coluna_valor(df):
    keywords = ['total', 'venda', 'comissão', 'commission', 'gasto', 'spent', 'amount', 'valor', 'price', 'receita', 'faturamento']
    for col in df.columns:
        if any(k in str(col).lower() for k in keywords):
            return col
    return None

def processar_planilha(file):
    try:
        # Tenta ler CSV com separadores diferentes ou Excel
        if file.name.endswith('.csv'):
            try:
                df = pd.read_csv(file)
            except:
                df = pd.read_csv(file, encoding='latin1', sep=';') 
        else:
            df = pd.read_excel(file)

        col_data = encontrar_coluna_data(df)
        col_valor = encontrar_coluna_valor(df)

        if col_data and col_valor:
            # Converter data
            df['Data_Convertida'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce').dt.date
            
            # Limpar valores monetários
            df[col_valor] = df[col_valor].apply(limpar_moeda)
            
            # Remover datas inválidas
            df = df.dropna(subset=['Data_Convertida'])
            
            return df.groupby('Data_Convertida')[col_valor].sum().reset_index()
        else:
            return None
    except Exception as e:
        st.error(f"Erro detalhado ao ler {file.name}: {e}")
        return None

# --- PROCESSAMENTO PRINCIPAL ---
if shopee_file and meta_file:
    df_shopee = processar_planilha(shopee_file)
    df_meta = processar_planilha(meta_file)

    if df_shopee is not None and df_meta is not None:
        df_shopee.columns = ['Data', 'Receita']
        df_meta.columns = ['Data', 'Custo']

        df_final = pd.merge(df_shopee, df_meta, on='Data', how='outer').fillna(0)
        df_final['Saldo'] = df_final['Receita'] - df_final['Custo']
        df_final = df_final.sort_values('Data')

        # --- FILTRO DE DATA ---
        if not df_final.empty:
            min_date = df_final['Data'].min()
            max_date = df_final['Data'].max()
            
            st.sidebar.markdown("---")
            st.sidebar.subheader("📅 Filtrar Período")
            try:
                start_date, end_date = st.sidebar.date_input(
                    "Selecione o intervalo:",
                    [min_date, max_date],
                    min_value=min_date,
                    max_value=max_date
                )
            except:
                start_date, end_date = min_date, max_date

            mask = (df_final['Data'] >= start_date) & (df_final['Data'] <= end_date)
            df_filtered = df_final.loc[mask]

            # --- METRICS ---
            col1, col2, col3 = st.columns(3)
            receita_total = df_filtered['Receita'].sum()
            custo_total = df_filtered['Custo'].sum()
            saldo_total = df_filtered['Saldo'].sum()
            roi = ((receita_total - custo_total) / custo_total) * 100 if custo_total > 0 else 0

            col1.metric("💰 Faturamento Shopee", f"R$ {receita_total:,.2f}")
            col2.metric("💸 Gasto Meta Ads", f"R$ {custo_total:,.2f}")
            col3.metric("📈 Lucro Líquido", f"R$ {saldo_total:,.2f}", delta=f"{roi:.1f}% ROI")

            # --- GRÁFICOS ---
            st.markdown("### 📊 Evolução Diária")
            fig = px.line(df_filtered, x='Data', y=['Receita', 'Custo', 'Saldo'], 
                          color_discrete_map={'Receita': '#00bfa5', 'Custo': '#ef4444', 'Saldo': '#3b82f6'},
                          markers=True)
            fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="white")
            st.plotly_chart(fig, use_container_width=True)

            with st.expander("Ver Tabela Detalhada"):
                st.dataframe(df_filtered.style.format("R$ {:.2f}", subset=['Receita', 'Custo', 'Saldo']), use_container_width=True)
        else:
            st.warning("As planilhas foram lidas, mas não há dados comuns para exibir.")
    else:
        st.warning("Não foi possível identificar as colunas de Data e Valor. Verifique se os arquivos não estão vazios.")

else:
    st.info("👋 Olá! Faça o upload dos relatórios na barra lateral.")
