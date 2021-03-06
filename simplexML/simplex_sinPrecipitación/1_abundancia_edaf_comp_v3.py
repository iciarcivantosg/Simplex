"""
En este script se utiliza información sobre componentes abióticos y componentes bióticos (número de individuos de otras especies
también presentes en el subplot) para predecir el número
de individuals que aparecerán en un determinado subplot.

"""
import random

import pandas as pd
pd.set_option('display.max_colwidth', -1)
import numpy as np

from sklearn import metrics
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.model_selection import cross_validate
from sklearn.metrics import mean_squared_error

import rse
import xgboost


"""
Dado que  se va a trabajar con componentes abióticos y bióticos, se cargarán ambos datasets y se realiza un merge de ambos  utilizando el índice como
columna de unión. Inicialmente en los dataset están presentes columnas que no se van a utilizar para
la predicción. Estas son: year, month, day, plotID, x, y, subplot. Además, existen columnas duplicadas en ambos datasets, por este motivo se 
realiza una selección de las variables que se utilizarán para entrenar el modelo.

Estas variables son las incluidas en col_list
"""

print("=================================================")
print("Predictor with environmental and competition data")
print("=================================================")


environment_train = pd.read_csv('datasets/abund_merged_dataset_onlyenvironment.csv', sep=',')
competitors_train = pd.read_csv('datasets/abund_merged_dataset_onlycompetitors.csv', sep=',')

individuals_train = environment_train.merge(competitors_train)
 

num_rows = len(individuals_train)
num_cols = len(individuals_train.columns)
print("This dataset has {0} rows and {1} columns".format(num_rows, num_cols))


col_list = ['species', 'individuals', 'present',
       'ph', 'salinity', 'cl', 'co3', 'c', 'mo', 'n', 'cn', 'p', 'ca', 'mg',
       'k', 'na', 'BEMA', 'CETE', 'CHFU', 'CHMI', 'COSQ', 'FRPU', 'HOMA', 'LEMA', 'LYTR',
       'MEEL', 'MEPO', 'MESU', 'PAIN', 'PLCO', 'POMA', 'POMO', 'PUPA', 'RAPE',
       'SASO', 'SCLA', 'SOAS', 'SPRU', 'SUSP']

individuals_train = individuals_train[col_list]
individuals_types = individuals_train.dtypes

"Data Wrangling"

"Transformamos la variable species a numérica"
le = LabelEncoder()
le.fit(individuals_train[['species']])
individuals_train[['species']] = le.transform(individuals_train[['species']])


"Transformamos la variable present a numérica"
le = LabelEncoder()
le.fit(individuals_train[['present']])
individuals_train[['present']] = le.transform(individuals_train[['present']])

"""
La variable present indica si el número de individuals en ese terreno es mayor que 0 (True) o no.
Hay un 25% de los datos en los que present es True, es decir, que sólo en el 25% de las filas
el número de individuals es > 0. Se planteo hacer un SMOTE para balancear el dataset, pero los
resultados empeoraban, por lo que se descartó.

"""

"""
También se estudió la reducción de la dimensionalidad a partir de la técnica "del canario". Consiste
en intruducir una variable de ruido aleatorio para posteriormente analizar qué variables en mi
dataset aportan más información que ese ruido aleatorio. 
En este caso, partiendo de un conjunto inicial de 40 variables el algoritmo seleccionaba como más importantes:
- 0	PAIN	0.1993726098053827
- 1	present	0.17199974018884817
- 2	species	0.15816533700741336
- 3	HOMA	0.0827913900673997
- 4	precip	0.07475141474783535
- 5	LEMA	0.03448362128281919
- 6	CHFU	0.026717495138886056
- 7	POMA	0.025132994728885853
- 8	SASO	0.02208463009866737
- 9	co3	0.016149319067118327

En este subconjunto de variables se recogen componentes abióticos que ya fueron identificados como aquellas variables que aportaban mayor información
a la predicción de individuos en el modelo de 1_abundancia_edaf. Pero también se destacan ciertas especies. Tras realizar la predicción utilizando
únicamente estas variables se ha confirmado que no aportan mejores resultados dada la naturaleza del dataset, por lo
que se descartó la reducción de la dimensionalidad.

"""


"Feature Importance"

input_features = [column for column in list(individuals_train) if column != 'individuals']
X = individuals_train[input_features]
X['random_noise'] = np.random.normal(size=X.shape[0])
y = individuals_train['individuals']

# RF K-Fold train
print("RF K-Fold train")
classifier = RandomForestRegressor(n_jobs=-1)
cv = cross_validate(estimator=classifier, X=X, y=y, cv=5,return_estimator=True)

feature_importance = {}
for k in range(0, len(cv['estimator'])):
    feature_importance['k_{}'.format(k + 1)] = cv['estimator'][k].feature_importances_
feature_importance = pd.DataFrame(feature_importance, index=X.columns)

feature_importance = feature_importance.mean(axis=1).to_frame('importance') \
        .sort_values('importance', ascending=False)
feature_selection = feature_importance.to_dict()

# Get importance concentration score
importance_concentration = (feature_importance.iloc[1] / feature_importance.iloc[0]).values[0] < 0.10
feature_selection['importance_concentration'] = {'assessment': importance_concentration,
                                                 'score': 1 if importance_concentration else 3}

# Get selected features score
selected_features = feature_importance['importance'] > feature_importance.loc['random_noise'].values[0]
selected_features = feature_importance.index[selected_features].tolist()

feature_importance.reset_index(inplace = True)

"""
Dado que se descartó la reducción de dimensionalidad, se utilizarán todas las variables para
entrenar el modelo. La variable individuals es la que queremos predecir, es el número
de individuos que aparecerán en un subplot, en función de las condiciones abióticas.

Para la separación train y test en este caso se utiliza un random split (en otro script se
utilizan unos años como train y el último año como test).
"""


"Estandarizacion de los datos"

variables_to_ignore = ['individuals']
selected_features = [element for element in list(individuals_train) if element not in variables_to_ignore]

individuals_model_train = individuals_train[selected_features]

std_scaler = StandardScaler()

std_scaler_model = std_scaler.fit(individuals_model_train)
individuals_model_train = std_scaler_model.transform(individuals_model_train)



"Division Train Test"

X = pd.DataFrame(data = individuals_model_train, columns = selected_features)
y = individuals_train.individuals

X_train, X_test, y_train, y_test = train_test_split(X, y, train_size= 0.8)
print(X_train.columns)

"Algoritmos y Evaluación"

"Linear Regression"

reg = LinearRegression()
reg.fit(X_train,y_train)

predictions_lr = reg.predict(X_test)

rmse_lr = np.sqrt(metrics.mean_squared_error(y_test, predictions_lr))
mse_lr = mean_squared_error(y_test,predictions_lr)
rse_lr = rse.calc_rse(y_test,predictions_lr)

print("mse {:.4f} rmse {:.4f} rse {:.4f}".format(mse_lr,rmse_lr,rse_lr))


"Random Forest"

n_estimators = [100, 150]
max_features = ['auto']
random_grid = {'n_estimators': n_estimators,
           'max_features': max_features}

seed_value = 4
random.seed(seed_value)


regr = RandomForestRegressor( n_jobs = -1)
# regr = RandomForestRegressor(random_state= seed_value, n_jobs = -1, n_estimators = 150)
regr_random = RandomizedSearchCV(estimator = regr, param_distributions = random_grid, cv = 7, verbose=2, n_jobs = -1)

regr_random.fit(X_train,y_train)
predictions_rf = regr_random.best_estimator_.predict(X_test)


rmse_rf = np.sqrt(metrics.mean_squared_error(y_test, predictions_rf))
mse_rf = mean_squared_error(y_test,predictions_rf)
rse_rf = rse.calc_rse(y_test,predictions_rf)

print("mse {:.4f} rmse {:.4f} rse {:.4f}".format(mse_rf,rmse_rf,rse_rf))

"XGBoost Regressor"


xgb = xgboost.XGBRegressor()
xgb.fit(X_train,y_train)

predictions_xgb = xgb.predict(X_test)

rmse_xgb = np.sqrt(metrics.mean_squared_error(y_test, predictions_xgb))
mse_xgb = mean_squared_error(y_test,predictions_xgb)
rse_xgb = rse.calc_rse(y_test,predictions_xgb)

print("mse {:.4f} rmse {:.4f} rse {:.4f}".format(mse_xgb,rmse_xgb,rse_xgb))