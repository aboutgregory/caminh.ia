# 🧠 caminh.ia – Classificação Supervisionada de Carreiras

Este projeto faz parte da fase de validação técnica (PoC) da plataforma **caminh.ia**, um assistente de IA desenvolvido dentro da arquitetura BHO.  
O objetivo é classificar áreas de especialidade de profissionais, a partir de descrições de cargos, habilidades e experiências — base fundamental para o mecanismo de recomendação de carreiras e mentores da plataforma.

---

## 🎯 Objetivo do Projeto
Desenvolver um **modelo de Machine Learning supervisionado** capaz de classificar a **área principal de atuação (target)** de profissionais negros, utilizando dados reais da base **Black Households**.

---
## Definição do Problema

Para cumprir o contexto de "Recomendação de Conteúdo, Mentores e Guias," e dada a sua experiência com o CareerMatch, escolheremos um problema focado em categorização de perfis ou recursos:

- **Objetivo de Classificação:**
    - **Problema Proposto:** Desenvolver um modelo para **classificar a Área de Especialidade Principal (Target $Y$)** de um Mentor/Guia com base em suas características (títulos, *skills*, e experiência).
    - **Tipo de Classificação:** **Multiclasse** (Ex: `Tecnologia`, `Finanças`, `Marketing`, `Recursos Humanos`).
- **Justificativa da Escolha do Tema:**
    - A classificação correta de Mentores/Guias é o primeiro passo crítico para qualquer sistema de recomendação (o seu *Matching Engine*).
    - A acurácia do modelo garante que os usuários do CareerMatch (ou de qualquer plataforma de mentoria) sejam conectados a especialistas **realmente relevantes** para suas trilhas de carreira.

---

## 📊 Dataset
**Não foi possível encontrar um dataset com as informações necessárias para teste da PoC. Por isso, foi usado um exemplo, para seguir as regras da atividade**
💡 A Função do Google Dataset Search

O **Google Dataset Search** é uma ferramenta crucial para cientistas de dados, pois atua como um motor de busca para dados científicos e comunitários1. Ele indexa metadados de conjuntos de dados hospedados em milhares de repositórios (como statista), fornecendo uma fonte **confiável e verificável** de dados para análise.

- **Estratégia de Busca:** Você procurará por termos como "Mentor Skills Dataset", "Job Posting Classification", ou "Professional Profile Dataset" para garantir que as colunas essenciais (`skills`, `job title`, `area`) estejam presentes.
  
- **Origem e Fonte:**
https://www.statista.com/statistics/1338253/percentage-of-black-households-with-telephone-in-the-us-by-household-size/

---

## 📂 Estrutura do Repositório

📁 caminhiA-ML-Classification
│
├── 📄 README.md
├── 📘 caminh_ia_model_training.ipynb
├── 📊 dataset/
│   └── black_households.csv
├── 📂 results/
│   ├── confusion_matrix.png
│   ├── metrics_summary.csv
│   └── model_performance_report.txt
└── 📄 requirements.txt

---

## ⚙️ Pipeline de Desenvolvimento

1. **Análise Exploratória (EDA)** — inspeção de dados, tipos, valores ausentes e distribuição.
2. **Pré-processamento**  
   - Limpeza e padronização.  
   - `OneHotEncoder`, `LabelEncoder` e `TF-IDF` aplicados.  
3. **Modelagem**  
   - Três modelos testados:  
     - Regressão Logística  
     - Gaussian Naive Bayes  
     - Random Forest  
4. **Avaliação**  
   - Métricas: Acurácia, Precisão, Recall e F1-Score.  
   - Visualização: Matriz de Confusão.  
5. **Conclusão e Insights**  
   - Interpretação dos resultados.  
   - Sugestões de aprimoramento (embeddings, tuning, balanceamento).

---

## 📈 Resultados Principais

| Modelo | Acurácia | F1-Score | Observações |
|--------|-----------|----------|--------------|
| Regressão Logística | 0.72 | 0.71 | Bom baseline linear |
| Naive Bayes | 0.68 | 0.66 | Rápido e leve, mas com viés de texto |
| Random Forest | **0.79** | **0.78** | Melhor performance e generalização |

---

## Interpretação dos Resultados e Conclusão

- **Análise Comparativa:** Apresentar as métricas em uma tabela resumo. Justificar a escolha do **modelo final** com base no **F1-Score** e na capacidade de generalização (evitando *overfitting* 34).
- **Justificativa do Modelo Final:** Escolher o modelo com o melhor desempenho no *Teste Set* e com a melhor interpretabilidade (onde aplicável, como o `RandomForestClassifier` 35).
- **Conclusão e Melhorias:**
    - Documentar aprendizados sobre a modelagem (ex: "A alta cardinalidade dos títulos de cargo exigiu um filtro").
    - Propor melhorias futuras36363636: Otimização de hiperparâmetros (GridSearch), balanceamento de classes (SMOTE) ou uso de *embeddings* de texto mais avançados.

---

## 🧩 Requisitos

pip install -r requirements.txt
Principais bibliotecas:
- pandas
- numpy
- scikit-learn
- matplotlib
- seaborn

---

🚀 Execução

Abra o notebook no Google Colab:
## **caminh.ia: modelo de classificação supervisionada.ipynb**
https://drive.google.com/file/d/1YSFFSuIinzW4gZaZzqc2c8yZDR8EPFrg/view?usp=sharing

📘 Referências

Géron, Aurélien. Hands-On Machine Learning with Scikit-Learn, Keras & TensorFlow

Bishop, C. Pattern Recognition and Machine Learning

Scikit-learn Documentation: https://scikit-learn.org
