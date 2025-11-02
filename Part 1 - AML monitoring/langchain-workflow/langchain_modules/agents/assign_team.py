import datetime

def assign_team(row):
    # Front Office
    if (row["edd_required"] == True and row["edd_performed"] == False) or \
       (row["kyc_due_date"] < datetime.now().strftime("%Y-%m-%d")) or \
       (row["suitability_assessed"] == False):
        return "Front Office"
    
    if row['flagged'] == 1:
        return "Legal and Compliance Team"