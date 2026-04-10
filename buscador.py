
# Motor de filtragem dinâmico.

#      Estruturas dos filtros
#      Estrutura 1 SIMPLES -> [coluna, tipo, ['palavra1','palavra2'], 'nome do filtro'],
#      Estrutura 2 COMPOSTO -> [coluna, tipo, ['gatilho1','gatilho2'], ['palavra1','palavra2'], 'nome do filtro'],


#     0 - Incluir se palavra exata existir.
#     1 - Excluir se palavra exata existir.                                     -->   [coluna, 1, ['EPIS','proteção'], "lixo"],
#     2 - Refinamento Condicional ([Gatilho] -> MANTÉM se tiver a [palavra]).
#     3 - Exclusão Condicional ([Gatilho] -> EXCLUI se tiver a [palavra]).      -->   [coluna, 3, ['bomba','BOMBEAMENTO'], ['manutenção','calor'], 'filtro bomba']
 


import pandas as pd
import re
import os

# ==========================================
# CLASSE BASE E FILTROS ESPECÍFICOS
# ==========================================

class Filtro:
    """Classe base para todos os filtros."""
    def __init__(self, coluna_idx, nome):
        self.coluna_idx = coluna_idx
        self.nome = nome

    def aplicar(self, dados):
        raise NotImplementedError("Cada filtro deve implementar seu próprio método aplicar.")

class FiltroSimples(Filtro):
    """Tipos 0 (Inclusão) e 1 (Exclusão) usando Regex."""
    def __init__(self, coluna_idx, tipo, palavras, nome):
        super().__init__(coluna_idx, nome)
        self.tipo = tipo  # 0 ou 1
        self.palavras = palavras

    def aplicar(self, item, nome_coluna):
        valor = str(item.get(nome_coluna, "")).lower()
        match_detectado = None
        
        for termo in self.palavras:
            padrao = r'\b' + re.escape(termo.lower()) + r'\b'
            if re.search(padrao, valor):
                match_detectado = termo.lower()
                break
        
        if self.tipo == 0:  # Inclusão
            if match_detectado:
                item['Termo_Match'] = match_detectado
                return item
        elif self.tipo == 1:  # Exclusão
            if not match_detectado:
                return item
        return None

class FiltroCondicional(Filtro):
    """Tipos 2 (Manutenção) e 3 (Exclusão Condicional)."""
    def __init__(self, coluna_idx, tipo, gatilhos, adicionais, nome):
        super().__init__(coluna_idx, nome)
        self.tipo = tipo  # 2 ou 3
        self.gatilhos = [g.lower() for g in gatilhos]
        self.adicionais = [a.lower() for a in adicionais]

    def aplicar(self, item, nome_coluna):
        valor = str(item.get(nome_coluna, "")).lower()
        tem_gatilho = any(g in valor for g in self.gatilhos)
        
        if tem_gatilho:
            tem_termo_ref = any(p in valor for p in self.adicionais)
            if self.tipo == 2 and tem_termo_ref: return item
            if self.tipo == 3 and not tem_termo_ref: return item
            return None
        return item  # Se não tem gatilho, passa direto

# ==========================================
# GERENCIADOR DO MOTOR
# ==========================================

class MotorFiltragem:
    def __init__(self, titulo):
        self.titulo = titulo
        self.filtros = []
        self.historico_abas = []

    def adicionar_filtro(self, filtro_obj):
        self.filtros.append(filtro_obj)
        print(f"➕ Filtro '{filtro_obj.nome}' adicionado.")

    def remover_filtro(self, nome_filtro):
        self.filtros = [f for f in self.filtros if f.nome != nome_filtro]
        print(f"🗑️ Filtro '{nome_filtro}' removido.")

    def processar(self, df_inicial):
        dados_atuais = df_inicial.to_dict(orient='records')
        self.historico_abas = [("0_Base_Original", df_inicial.copy())]

        for filtro in self.filtros:
            nome_coluna = list(dados_atuais[0].keys())[filtro.coluna_idx]
            novos_dados = []

            for item in dados_atuais:
                resultado = filtro.aplicar(item.copy(), nome_coluna)
                if resultado:
                    novos_dados.append(resultado)
            
            dados_atuais = novos_dados
            if not dados_atuais:
                print(f"⚠️ O funil parou em '{filtro.nome}': 0 itens restantes.")
                break
            
            self.historico_abas.append((filtro.nome, pd.DataFrame(dados_atuais)))
            print(f"✅ Etapa '{filtro.nome}' concluída ({len(dados_atuais)} itens).")

    def salvar(self, caminho_saida):
        if not self.historico_abas: return
        
        with pd.ExcelWriter(caminho_saida, engine='openpyxl') as writer:
            for nome, df in reversed(self.historico_abas):
                # Limpa coluna de match se não for a aba de inclusão
                if 'Termo_Match' in df.columns and nome == "0_Base_Original":
                     df = df.drop(columns=['Termo_Match'])
                
                df.to_excel(writer, sheet_name=nome[:31], index=False)
        print(f"\n✨ Relatório '{self.titulo}' gerado com sucesso!")

# ==========================================
# EXECUÇÃO 
# ==========================================

if __name__ == "__main__":
    # 1. Instanciar o Motor
    motor = MotorFiltragem("Relatorio de Ativos")

    # 2. Adicionar os filtros usando a nova estrutura
    motor.adicionar_filtro(FiltroSimples(8, 0, ['BOOSTER','SBL','BOMBEAMENTO','BOMBA','reservatório', 'reservatorio','tanque','estação','estacao','ETE','ETA','EEE','abraçadeira','abracadeira','acoplamento', ], "Filtro 1"))
    motor.adicionar_filtro(FiltroCondicional(8, 3, ['bomba','BOMBEAMENTO'], ['manutenção','calor','concreto','combustível','dosadoras','dosador','SUCÇÃO','banheiro','banheiros',], 'filtro bomba'))
    motor.adicionar_filtro(FiltroCondicional(8, 3, ['estação','estacao','ETE','ETA','EEE'], ['prfv','Remoção','limpeza','manutenção','Rádio','REFORMA','laboratoriais','laboratorial'], 'filtro estação'))
    
    motor.adicionar_filtro(FiltroSimples(8, 1, ['EPIS','proteção','incendio','incendios','ferramentas','salas','CARRETA','caminhão','ares-condicionados','ar-condicionado','pipa'], "lixo"))
    motor.adicionar_filtro(FiltroSimples(8, 1, ['manutenção', 'limpeza'], "Filtro manutenção"))
    motor.adicionar_filtro(FiltroSimples(5, 1, ['urgente'], "Filtro urgente"))


    # 3. Executar (supondo que o arquivo exista)
    if os.path.exists('dados.xlsm'):
        df = pd.read_excel('dados.xlsm', sheet_name=-1)
        motor.processar(df)
        motor.salvar('relatorio_final.xlsx')


































# import pandas as pd
# import os
# import re

# ARQUIVO_ENTRADA  = 'dados.xlsm'
# ARQUIVO_SAIDA    = 'relatorio.xlsx'


# CONFIG = [
#     # procura universal
#     [8, 0, [
#         'BOOSTER','SBL','BOMBEAMENTO','BOMBA','reservatório', 'reservatorio','tanque',
#         'estação','estacao','ETE','ETA','EEE','abraçadeira','abracadeira','acoplamento', 
#         ], "Filtro 1"
#     ],


#     [8, 3, ['bomba','BOMBEAMENTO'], ['manutenção','calor','concreto','combustível','dosadoras','dosador','SUCÇÃO','banheiro','banheiros',], 'filtro bomba'],
#     [8, 3, ['estação','estacao','ETE','ETA','EEE'], ['prfv','Remoção','limpeza','manutenção','Rádio','REFORMA','laboratoriais','laboratorial'], 'filtro estação'],
#     # [8, 3, ['abraçadeira','abracadeira','acoplamento'], [], 'filtro 3']

#     [8, 1, ['EPIS','proteção','incendio','incendios','ferramentas','salas','CARRETA','caminhão','ares-condicionados','ar-condicionado','pipa'], "lixo"],
#     [8, 1, ['manutenção', 'limpeza'], "Filtro manutenção"],
#     [5, 1, ['urgente'], "Filtro urgente"],
# ]



# # ==========================================
# # 2. FUNÇÕES DE PROCESSAMENTO
# # ==========================================

# def carregar_base(caminho):
#     xl = pd.ExcelFile(caminho, engine='openpyxl')
#     aba_alvo = xl.sheet_names[-1]
#     return pd.read_excel(caminho, sheet_name=aba_alvo, engine='openpyxl')


# def processar_filtro_dinamico(dados_lista, col_idx, tipo_filtro, keywords, adicionais=None):
#     """
#     Motor de filtragem dinâmico.
#     0 - Incluir se palavra exata existir.
#     1 - Excluir se palavra exata existir.
#     2 - Refinamento Condicional (Gatilho -> MANTÉM se tiver a palavra).
#     3 - Exclusão Condicional (Gatilho -> EXCLUI se tiver a palavra).
#     """

#     if not dados_lista: return []
    
#     resultado = []
#     nome_coluna = list(dados_lista[0].keys())[col_idx]

#     for item in dados_lista:
#         valor_celula = str(item.get(nome_coluna, "")).lower()
        
#         # --- LÓGICA PARA TIPO 2 e 3 (Condicionais) ---
#         if tipo_filtro in [2, 3]:
#             gatilhos = [g.lower() for g in keywords]
#             termos_ref = [p.lower() for p in adicionais] if adicionais else []
            
#             tem_gatilho = any(g in valor_celula for g in gatilhos)
            
#             if tem_gatilho:
#                 tem_termo_ref = any(p in valor_celula for p in termos_ref)
                
#                 if tipo_filtro == 2:
#                     # Tipo 2: Se tem gatilho, precisa ter o termo para ficar
#                     if tem_termo_ref:
#                         resultado.append(item.copy())
                
#                 elif tipo_filtro == 3:
#                     # Tipo 3: Se tem gatilho e tem o termo proibido, descarta (não adiciona)
#                     if not tem_termo_ref:
#                         resultado.append(item.copy())
#             else:
#                 # Se não tem o gatilho (ex: é reservatório), passa direto intacto
#                 resultado.append(item.copy())
            
#             continue # Vai para o próximo item

#         # --- LÓGICA PARA TIPO 0 e 1 (Regex) ---
#         match_detectado = None
#         for termo in keywords:
#             termo_lower = termo.lower()
#             padrao = r'\b' + re.escape(termo_lower) + r'\b'
#             if re.search(padrao, valor_celula):
#                 match_detectado = termo_lower
#                 break

#         if tipo_filtro == 0:
#             if match_detectado:
#                 novo_item = item.copy()
#                 novo_item['Termo_Match'] = match_detectado
#                 resultado.append(novo_item)
        
#         elif tipo_filtro == 1:
#             if not match_detectado:
#                 resultado.append(item.copy())

#     return resultado




# # ==========================================
# # 3. EXECUÇÃO
# # ==========================================

# if __name__ == "__main__":
#     # 1. Configuração de Caminhos
#     diretorio = os.path.dirname(os.path.abspath(__file__))
#     caminho_in = os.path.join(diretorio, ARQUIVO_ENTRADA)
#     caminho_out = os.path.join(diretorio, ARQUIVO_SAIDA)

#     # 2. Verificação de existência do arquivo
#     if os.path.exists(caminho_in):
#         print(f"📖 Carregando base: {ARQUIVO_ENTRADA}")
#         df_base = carregar_base(caminho_in)
        
#         # Converte o DataFrame para lista de dicionários para processamento rápido
#         dados_atuais = df_base.to_dict(orient='records')
        
#         # Pilha para armazenar os DataFrames de cada aba (Nome, DataFrame)
#         pilha_abas = [("0_Base_Original", df_base)]

#         print("🔍 Iniciando processamento dos filtros...")
        
#         # 3. Loop Principal de Filtragem
#         for item_config in CONFIG:
#             # Identifica o Tipo de Filtro (posição 1 da lista)
#             tipo = item_config[1]
            
#             # Ajusta o desempacotamento conforme o tipo de filtro
#             if tipo in [2, 3]:
#                 # Formato esperado: [col, tipo, [gatilhos], [adicionais], "nome"]
#                 if len(item_config) < 5:
#                     print(f"❌ Erro na CONFIG: Filtro Tipo {tipo} exige 5 parâmetros.")
#                     continue
#                 col_idx, _, termos, adicionais, nome_aba = item_config
#             else:
#                 # Formato esperado: [col, tipo, [termos], "nome"]
#                 col_idx, _, termos, nome_aba = item_config
#                 adicionais = None # Não usado nos tipos 0 e 1

#             # Executa o motor de filtragem
#             dados_atuais = processar_filtro_dinamico(
#                 dados_atuais, 
#                 col_idx, 
#                 tipo, 
#                 termos, 
#                 adicionais
#             )
            
#             # Se houver resultados, salva na pilha de abas
#             if dados_atuais:
#                 df_resultado = pd.DataFrame(dados_atuais)
#                 # Remove a coluna auxiliar de match se ela existir (opcional, para limpeza)
#                 if 'Termo_Match' in df_resultado.columns and tipo != 0:
#                      df_resultado = df_resultado.drop(columns=['Termo_Match'])
                
#                 pilha_abas.append((nome_aba, df_resultado))
#                 print(f"✅ Etapa '{nome_aba}' concluída ({len(dados_atuais)} itens).")
#             else:
#                 print(f"⚠️ Etapa '{nome_aba}' resultou em 0 itens. O funil parou aqui.")
#                 break

#         # 4. Geração do arquivo Excel de saída
#         print(f"💾 Gerando arquivo de saída: {ARQUIVO_SAIDA}...")
        
#         # Invertemos a ordem para que o último filtro (mais importante) apareça primeiro
#         pilha_ordenada = list(reversed(pilha_abas))

#         try:
#             with pd.ExcelWriter(caminho_out, engine='openpyxl') as writer:
#                 for nome, df in pilha_ordenada:
#                     # Limita o nome da aba a 31 caracteres (limite do Excel)
#                     nome_curto = nome[:31]
#                     df.to_excel(writer, sheet_name=nome_curto, index=False)
            
#             print(f"\n✨ Sucesso! O relatório foi gerado com {len(pilha_abas)} abas.")
            
#         except Exception as e:
#             print(f"❌ Erro ao salvar o arquivo Excel: {e}")

#     else:
#         print(f"❌ Erro: O arquivo de entrada '{ARQUIVO_ENTRADA}' não foi encontrado no diretório.")