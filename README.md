# 🧠 caminh.ia – Classificação Supervisionada de Carreiras

Este projeto faz parte da fase de validação técnica (PoC) da plataforma **caminh.ia**, um assistente de IA desenvolvido dentro da arquitetura BHO.  
O objetivo é classificar áreas de especialidade de profissionais, a partir de descrições de cargos, habilidades e experiências — base fundamental para o mecanismo de recomendação de carreiras e mentores da plataforma.

---

## 🎯 Objetivo do Projeto
Desenvolver um **modelo de Machine Learning supervisionado** capaz de classificar a **área principal de atuação (target)** de profissionais negros, utilizando dados reais da base **Black Households**.

---

## 📊 Dataset
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
