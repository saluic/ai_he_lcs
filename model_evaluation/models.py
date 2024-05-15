from math import exp
import pandas as pd

def plcom2012(X):
    required_columns = [
        'age',
        'race',
        'education',
        'bmi',
        'copd',
        'cancer_hist',
        'family_hist_lung_cancer',
        'smoking_status',
        'cig_day',
        'smoking_years',
        'quit_years'
    ]
    for c in required_columns:
        if c not in X.columns:
            print(
                f"Column {c} missing." +
                f"\nRequired columns: {required_columns}"
            )
            exit(1)
    return X.apply(_plcom2012_single, axis=1)

def _plcom2012_single(X):
    age = X['age']
    race = X['race']
    education = X['education']
    bmi = X['bmi']
    copd = X['copd']
    cancer_hist = X['cancer_hist']
    family_hist_lung_cancer = X['family_hist_lung_cancer']
    smoking_status = X['smoking_status']
    smoking_intensity = X['cig_day']
    duration_smoking = X['smoking_years']
    smoking_quit_time = X['quit_years']

    model = 0
    if race == 1 or race == 4: # White, American Indian or Alaskan Native
        model = (0.0778868 * (age - 62) - 0.0812744 * (education - 4) - 0.0274194 * (bmi - 27) + 0.3553063 * copd + 0.4589971 * cancer_hist +
            0.587185 * family_hist_lung_cancer + 0.2597431 * smoking_status - 1.822606 * ((smoking_intensity/10)**(-1) - 0.4021541613) + 0.0317321 *
            (duration_smoking - 27) - 0.0308572 * (smoking_quit_time - 10) - 4.532506)
        
    elif race == 2: # Black or African American
        model = (0.0778868 * (age - 62) - 0.0812744 * (education - 4) - 0.0274194 * (bmi - 27) + 0.3553063 * copd + 0.4589971 * cancer_hist +
            0.587185 * family_hist_lung_cancer + 0.2597431 * smoking_status - 1.822606 * ((smoking_intensity/10)**(-1) - 0.4021541613) + 0.0317321 *
            (duration_smoking - 27) - 0.0308572 * (smoking_quit_time - 10) - 4.532506 + 0.3944778)
        
    elif race == 8: # Hispanic or Latino
        model = (0.0778868 * (age - 62) - 0.0812744 * (education - 4) - 0.0274194 * (bmi - 27) + 0.3553063 * copd + 0.4589971 * cancer_hist +
            0.587185 * family_hist_lung_cancer + 0.2597431 * smoking_status - 1.822606 * ((smoking_intensity/10)**(-1) - 0.4021541613) + 0.0317321 *
            (duration_smoking - 27) - 0.0308572 * (smoking_quit_time - 10) - 4.532506 - 0.7434744)
        
    elif race == 3: # Asian
        model = (0.0778868 * (age - 62) - 0.0812744 * (education - 4) - 0.0274194 * (bmi - 27) + 0.3553063 * copd + 0.4589971 * cancer_hist +
            0.587185 * family_hist_lung_cancer + 0.2597431 * smoking_status - 1.822606 * ((smoking_intensity/10)**(-1) - 0.4021541613) + 0.0317321 *
            (duration_smoking - 27) - 0.0308572 * (smoking_quit_time - 10) - 4.532506 - 0.466585)
        
    elif race == 5: # Native Hawaiian or Other Pacific Islander
        model = (0.0778868 * (age - 62) - 0.0812744 * (education - 4) - 0.0274194 * (bmi - 27) + 0.3553063 * copd + 0.4589971 * cancer_hist +
            0.587185 * family_hist_lung_cancer + 0.2597431 * smoking_status - 1.822606 * ((smoking_intensity/10)**(-1) - 0.4021541613) + 0.0317321 *
            (duration_smoking - 27) - 0.0308572 * (smoking_quit_time - 10) - 4.532506 + 1.027152)
    
    else:
        print("Race: no match:", race)
        return None
    
    prob = exp(model)/(1 + exp(model))
    return prob

if __name__ == '__main__':
    cols = ['age', 'race', 'education', 'bmi', 'copd', 'cancer_hist',
        'family_hist_lung_cancer', 'smoking_status', 'cig_day',
        'smoking_years', 'quit_years']
    data = [
        [60,1,4,30,1,0,0,1,20,40,0],
        [70,1,4,30,1,0,0,1,20,40,0]
    ]
    df = pd.DataFrame(data, columns=cols)

    result = plcom2012(df)
    print(result)