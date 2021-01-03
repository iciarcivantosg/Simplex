import pandas as pd
pd.set_option('display.max_colwidth', -1)
import numpy as np
import math
import seaborn as sns
sns.set(color_codes=True)
import xlsxwriter
from sklearn import metrics
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split, RandomizedSearchCV
from sklearn.metrics import mean_squared_error
from imblearn.over_sampling import SMOTE
import xgboost

import sys
import rse


if (len(sys.argv)>2):
    print("ERROR. Usage: 2_competitors_v3.py [present_percentage]")
    exit()
if (len(sys.argv) ==1):
    smote_yn = 'n'
else:
    perc_0s = float(sys.argv[1])
    smote_0s = round(perc_0s/100,2)
    smote_yn = 'y'

print("Two-step predictor")
print("======================")

environment_train = pd.read_csv('datasets/abund_merged_dataset_onlyenvironment.csv', sep=',')
competitors_train = pd.read_csv('datasets/abund_merged_dataset_onlycompetitors.csv', sep=',')

conditions = environment_train.merge(competitors_train)
 

num_rows = len(conditions)
num_cols = len(conditions.columns)
print("This dataset has {0} rows and {1} columns".format(num_rows, num_cols))


col_list = ['species', 'individuals',
       'ph', 'salinity', 'cl', 'co3', 'c', 'mo', 'n', 'cn', 'p', 'ca', 'mg',
       'k', 'na', 'precip', 'present',
       'BEMA', 'CETE', 'CHFU', 'CHMI', 'COSQ', 'FRPU', 'HOMA', 'LEMA', 'LYTR',
       'MEEL', 'MEPO', 'MESU', 'PAIN', 'PLCO', 'POMA', 'POMO', 'PUPA', 'RAPE',
       'SASO', 'SCLA', 'SOAS', 'SPRU', 'SUSP']

train_list = ['species', 'individuals', 
       'ph', 'salinity', 'cl', 'co3', 'c', 'mo', 'n', 'cn', 'p', 'ca', 'mg',
       'k', 'na', 'precip', 'present']

conditions = conditions[col_list]

conditions_types = conditions.dtypes

"Data Wrangling"

"Transformamos la variable species a numérica"
le = LabelEncoder()
le.fit(conditions[['species']])
conditions[['species']] = le.transform(conditions[['species']])

species_mapping = {l: i for i, l in enumerate(le.classes_)}
species_mapping_inv = {i: l for i, l in enumerate(le.classes_)}

"Transformamos la variable present a numérica"
le = LabelEncoder()
le.fit(conditions[['present']])
conditions[['present']] = le.transform(conditions[['present']])



perc_0s = round(len(np.where(conditions[['present']] == 0)[0])/num_rows * 100,2)
perc_1s = round(len(np.where(conditions[['present']] == 1)[0])/num_rows * 100,2)

print("===============================================")
print("Original proportion of cases: "+str(perc_0s)+"% of 0s"+\
      " and "+str(perc_1s)+"% of 1s")
print("===============================================")



if smote_yn == 'y':
    smote_0s = round(perc_0s/100,2)
    
    sm = SMOTE(random_state=42,sampling_strategy = smote_0s)
    conditions, y_res = sm.fit_resample(conditions[['species', 'individuals',
        'ph', 'salinity', 'cl', 'co3', 'c', 'mo', 'n', 'cn', 'p', 'ca', 'mg',
        'k', 'na', 'precip',
        'BEMA', 'CETE', 'CHFU', 'CHMI', 'COSQ', 'FRPU', 'HOMA', 'LEMA', 'LYTR',
        'MEEL', 'MEPO', 'MESU', 'PAIN', 'PLCO', 'POMA', 'POMO', 'PUPA', 'RAPE',
        'SASO', 'SCLA', 'SOAS', 'SPRU', 'SUSP']], conditions[['present']])
    conditions = conditions.join(y_res)
    
else:
    print("===============================================")
    print("No se aplicará SMOTE")
    print("===============================================")



"Estandarizacion de los datos"

conditions_model_train = conditions[train_list]

std_scaler = StandardScaler()
std_scaler_model = std_scaler.fit(conditions_model_train)
conditions_model_train = std_scaler_model.transform(conditions_model_train)


y_test_values = []
y_test_names = []
pred_values_lr = []
pred_values_rf = []
pred_values_xgb = []

for i in range(0, 50):
    
    print("============================================================================")
    print("============================================================================")
    print("============================================================================")
    print("============================================================================")
    print("============================================================================")
    print("======================== ITER: "+str(i)+" ==================================")
    print("============================================================================")
    print("============================================================================")
    print("============================================================================")
    print("============================================================================")

    y_pred = {}
    rmse_rf = {}
    rse_rf = {}
    
    
    
    features_to_pred = ['BEMA', 'CETE', 'CHFU', 'CHMI', 'COSQ', 'FRPU', 'HOMA', 'LEMA', 'LYTR',
           'MEEL', 'MEPO', 'MESU', 'PAIN', 'PLCO', 'POMA', 'POMO', 'PUPA', 'RAPE',
           'SASO', 'SCLA', 'SOAS', 'SPRU', 'SUSP']
    
    X = pd.DataFrame(data = conditions_model_train, columns = train_list)
    X[['present']] = conditions[['present']]
    y = conditions[features_to_pred]
    
    X_train_species, X_test_species, y_train_species, y_test_species = train_test_split(X, y, train_size= 0.8)
    
    species_scaled = conditions[['species']]    
    species_name = conditions.species.map(species_mapping_inv).tolist()    
    species_scaled['name'] = species_name
    species_id = species_scaled.name.map(species_mapping).tolist()    
    species_scaled['id'] = species_id
    species_scaled.reset_index(inplace = True)
    species_scaled = species_scaled.iloc[X_test_species.index]
    
    "Parámetros Random Forest"
    
    n_estimators = [100,150]
    max_features = ['auto']
    #Grid Search
    random_grid = {'n_estimators': n_estimators,
               'max_features': max_features}
    
    
    
    for i in range(0, len(features_to_pred)):
    
        variables_to_ignore = features_to_pred[i]
        print("--------------TARGET "+str(variables_to_ignore))
        
        "Division Train Test"
        
        
        X_train = X_train_species
        y_train = y_train_species[variables_to_ignore]
        
        X_test = X_test_species
        y_test = y_test_species[variables_to_ignore]
        
            
        "Algoritmos y Evaluación"
        
        "Random Forest"
        
        rf = RandomForestRegressor(n_jobs = -1)
        rf_random = RandomizedSearchCV(estimator = rf, param_distributions = random_grid, cv = 7, verbose=2, n_jobs = -1)
        
        rf_random.fit(X_train,y_train)
        predictions_rf = rf_random.best_estimator_.predict(X_test)
        
        y_pred[variables_to_ignore] = predictions_rf
    
    
    
    "Utilizamos los resultados para predecir individuals"
    
    features_to_pred = ['individuals']
    selected_features = [element for element in col_list if element not in features_to_pred]
    
    
    new_X = X_test_species.reset_index().drop(['index'], axis = 1)
    y_predictions = pd.DataFrame.from_dict(y_pred)
    y_predictions = y_predictions.applymap(lambda x: math.floor(x))
    X_individuals = new_X.join(y_predictions)[selected_features]
    
    y_individuals = conditions[features_to_pred].iloc[y_test_species.index].reset_index().drop(['index'], axis = 1)
    
    data = X_individuals.join(y_individuals)    
    data['species'] = species_scaled['id'].tolist()
    
    sm = SMOTE(random_state=42)
    data, y_res = sm.fit_resample(data[['species', 'individuals',
        'ph', 'salinity', 'cl', 'co3', 'c', 'mo', 'n', 'cn', 'p', 'ca', 'mg',
        'k', 'na', 'precip',
        'BEMA', 'CETE', 'CHFU', 'CHMI', 'COSQ', 'FRPU', 'HOMA', 'LEMA', 'LYTR',
        'MEEL', 'MEPO', 'MESU', 'PAIN', 'PLCO', 'POMA', 'POMO', 'PUPA', 'RAPE',
        'SASO', 'SCLA', 'SOAS', 'SPRU', 'SUSP']], data[['present']])
    data = data.join(y_res)
    
    
    X_ind = data[selected_features]
    y_ind = data['individuals']
    
    
    X_train_individuals, X_test_individuals, y_train_individuals, y_test_individuals = train_test_split(X_ind, y_ind, train_size= 0.8)
    
    y_test_values.extend(y_test_individuals.tolist())
    
    test_names = X_test_individuals.species.map(species_mapping_inv).tolist()
    y_test_names.extend(test_names)
    
    "Algoritmos y Evaluación"

    "Linear Regression"
    
    reg = LinearRegression()
    reg.fit(X_train_individuals,y_train_individuals)
    
    predictions_lr = reg.predict(X_test_individuals)
    
    pred_values_lr.extend(predictions_lr.tolist())
    
    "Random Forest"
    # print("Random Forest")
    seed_value = 4
    # random.seed(seed_value)
    
    rf = RandomForestRegressor(random_state= seed_value, n_jobs = -1, n_estimators = 150)
    rf.fit(X_train_individuals,y_train_individuals)
    predictions_rf = rf.predict(X_test_individuals)
    
    # rf = RandomForestRegressor(n_jobs = -1)
    # rf_random = RandomizedSearchCV(estimator = rf, param_distributions = random_grid, cv = 7, verbose=2, n_jobs = -1)
    
    # rf_random.fit(X_train_individuals,y_train_individuals)
    # predictions_rf = rf_random.best_estimator_.predict(X_test_individuals)
    
    pred_values_rf.extend(predictions_rf.tolist())
    
    
    "XGBoost Regressor"

    xgb = xgboost.XGBRegressor()
    xgb.fit(X_train_individuals,y_train_individuals)
    
    predictions_xgb = xgb.predict(X_test_individuals)
    
    pred_values_xgb.extend(predictions_xgb.tolist())

with xlsxwriter.Workbook('competitors.xlsx') as workbook:
    worksheet = workbook.add_worksheet('Linear_Regression')
    worksheet.write_row(0, 0, ['Specie Name','Real Values','Predictions'])
    for i,e in enumerate(y_test_names):
        worksheet.write(i + 1,0,e)
    for i,e in enumerate(y_test_values):
        worksheet.write(i + 1,1,e)
    for i,e in enumerate(pred_values_lr):
        worksheet.write(i + 1,2,e)
        
    worksheet = workbook.add_worksheet('Random_Forest')
    worksheet.write_row(0, 0, ['Specie Name','Real Values','Predictions'])
    for i,e in enumerate(y_test_names):
        worksheet.write(i + 1,0,e)
    for i,e in enumerate(y_test_values):
        worksheet.write(i + 1,1,e)
    for i,e in enumerate(pred_values_rf):
        worksheet.write(i + 1,2,e)
        
    worksheet = workbook.add_worksheet('XGBoost')
    worksheet.write_row(0, 0, ['Specie Name','Real Values','Predictions'])
    for i,e in enumerate(y_test_names):
        worksheet.write(i + 1,0,e)
    for i,e in enumerate(y_test_values):
        worksheet.write(i + 1,1,e)
    for i,e in enumerate(pred_values_xgb):
        worksheet.write(i + 1,2,e)
