import streamlit as st
import pandas as pd
import plotly.express as px
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Dashboard ROI - Shopee & Meta", page_icon="🚀", layout="wide")

# --- CSS CLEAN ---
st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    div[data-testid="stMetric"] {
        background-color: #1f2937; border: 1px solid #374151;
        padding: 15px; border-radius: 10px;
    }
    div[data-testid="stMetricLabel"] { color: #9ca3af; font-size: 14px; }
    div[data-testid="stMetricValue"] { color: #f3f4f6; font-size: 26px; }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 Analisador de Lucro: Shopee vs Ads")
st.markdown("---")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("📂 Importar Dados")
    shopee_file = st.file_uploader("Relatório Shopee", type=["csv", "xlsx"])
    meta_file = st.file_uploader("Relatório Meta Ads", type=["csv", "xlsx"])

# --- FUNÇÕES INTELIGENTES V3 ---

def encontrar_inicio_tabela(arquivo_bytes, encoding):
    """Procura a linha de cabeçalho decodificando o arquivo corretamente."""
    try:
        content = arquivo_bytes.getvalue().decode(encoding, errors='ignore')
        lines = content.split('\n')
        # Palavras-chave para identificar o cabeçalho
        keywords = ['order id', 'id do pedido', 'purchase time', 'data', 'date', 'campaign name', 'ad name']
        
        for i, line in enumerate(lines[:30]): # Escaneia até 30 linhas
            line_lower = line.lower()
            if sum(1 for k in keywords if k in line_lower) >= 1:
                return i
        return 0
    except:
        return 0

def ler_arquivo_robusto(file):
    """Tenta ler CSV/Excel com todas as combinações de codificação e separador."""
    if file.name.endswith('.xlsx'):
        return pd.read_excel(file)
    
    # Lista de tentativas para arquivos CSV "difíceis" (Shopee/Meta)
    encodings = ['utf-8', 'latin1', 'utf-16', 'cp1252']
    separators = [None, ',', ';', '\t'] # None = Auto-detectar (engine python)
    
    file_bytes = io.BytesIO(file.getvalue()) # Cria cópia segura dos dados
    
    for enc in encodings:
        try:
            # 1. Tenta descobrir onde começa a tabela com esse encoding
            file_bytes.seek(0)
            header_row = encontrar_inicio_tabela(file_bytes, enc)
            
            # 2. Tenta ler usando engine='python' (detecta separador sozinho)
            file.seek(0)
            return pd.read_csv(file, header=header_row, sep=None, engine='python', encoding=enc, on_bad_lines='skip')
        except:
            continue
            
    return None # Falhou todas as tentativas

def limpar_moeda(valor):
    if isinstance(valor, (int, float)): return valor
    if pd.isna(valor) or str(valor).strip() == '': return 0.0
    valor = str(valor).lower().replace('r$', '').replace('brl', '').replace('usd', '')
    valor = valor.replace('.', '').replace(',', '.') # Padrão PT-BR
    try: return float(valor.strip())
    except: return 0.0

def processar_planilha(file, nome_tipo):
    try:
        df = ler_arquivo_robusto(file)
        
        if df is None:
            return None, "Formato de arquivo não reconhecido (Tente salvar como CSV UTF-8 ou Excel)."

        if df.empty or len(df) == 0:
            return None, "Arquivo vazio (sem linhas de dados)."

        # Normalizar Colunas
        df.columns = [str(c).strip().lower() for c in df.columns]

        # 🔍 Debug: Se quiser ver as colunas que ele achou, descomente a linha abaixo
        # st.write(f"Colunas encontradas em {nome_tipo}:", list(df.columns))

        # Busca Inteligente de Colunas
        col_data = next((c for c in df.columns if any(k in c for k in ['date', 'data', 'time', 'tempo', 'day', 'created_at', 'starts'])), None)
        
        # Palavras-chave específicas para Shopee vs Meta
        if 'shopee' in nome_tipo.lower():
            keywords_valor = ['total amount', 'valor', 'comiss', 'income', 'receita', 'payable']
        else:
            keywords_valor = ['amount spent', 'gasto', 'cost', 'custo', 'valor', 'spent']
            
        col_valor = next((c for c in df.columns if any(k in c for k in keywords_valor)), None)

        if not col_data or not col_valor:
            return None, f"Colunas não achadas. Colunas lidas: {list(df.columns)[:5]}..."

        # Processar
        df = df.dropna(subset=[col_data])
        df['Data_Convertida'] = pd.to_datetime(df[col_data], dayfirst=True, errors='coerce').dt.date
        df = df.dropna(subset=['Data_Convertida']) # Remove datas inválidas
        
        if df.empty: return None, "Nenhuma data válida encontrada."

        df[col_valor] = df[col_valor].apply(limpar_moeda)
        
        return df.groupby('Data_Convertida')[col_valor].sum().reset_index(), "Sucesso"

    except Exception as e:
        return None, str(e)

# --- APP PRINCIPAL ---
if shopee_file and meta_file:
    df_s, status_s = processar_planilha(shopee_file, "Shopee")
    df_m, status_m = processar_planilha(meta_file, "Meta Ads")

    if df_s is None: st.warning(f"⚠️ Shopee: {status_s}")
    if df_m is None: st.warning(f"⚠️ Meta Ads: {status_m}")

    if df_s is not None and df_m is not None:
        df_s.columns = ['Data', 'Receita']
        df_m.columns = ['Data', 'Custo']
        
        # Merge
        df_final = pd.merge(df_s, df_m, on='Data', how='outer').fillna(0)
        df_final['Saldo'] = df_final['Receita'] - df_final['Custo']
        df_final = df_final.sort_values('Data')

        # --- EXIBIÇÃO ---
        min_date, max_date = df_final['Data'].min(), df_final['Data'].max()
        
        st.sidebar.markdown("---")
        if min_date == max_date:
            st.sidebar.info(f"📅 Data única: {min_date}")
            df_filtered = df_final
        else:
            r = st.sidebar.date_input("Período", [min_date, max_date], min_value=min_date, max_value=max_date)
            if isinstance(r, (list, tuple)) and len(r) == 2:
                df_filtered = df_final[(df_final['Data'] >= r[0]) & (df_final['Data'] <= r[1])]
            else:
                df_filtered = df_final

        c1, c2, c3 = st.columns(3)
        rec = df_filtered['Receita'].sum()
        cus = df_filtered['Custo'].sum()
        luc = df_filtered['Saldo'].sum()
        
        roi_val = ((rec - cus) / cus) * 100 if cus > 0 else 0
        
        c1.metric("💰 Shopee", f"R$ {rec:,.2f}")
        c2.metric("💸 Meta Ads", f"R$ {cus:,.2f}")
        c3.metric("📈 Lucro", f"R$ {luc:,.2f}", delta=f"{roi_val:.1f}% ROI")

        st.markdown("### 📊 Gráfico Diário")
        fig = px.line(df_filtered, x='Data', y=['Receita', 'Custo', 'Saldo'], markers=True,
                      color_discrete_map={'Receita': '#00C853', 'Custo': '#D50000', 'Saldo': '#2962FF'})
        fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font_color="white")
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(df_filtered.style.format("R$ {:.2f}", subset=['Receita', 'Custo', 'Saldo']), use_container_width=True)

else:
    st.info("👋 Aguardando uploads...")
