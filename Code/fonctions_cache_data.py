### ======== STAYOUT - Fonctions Cache Data ======== ### 

# ----------------------------
# IMPORTATIONS DES LIBRAIRIES
# ----------------------------
import os
import re
import stat
import shutil
import streamlit as st

# Récupération taille cache
def get_cache_size(path='.'):
    total_size = 0
    try:
        for path, names, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(path, f)
                if not os.path.islink(fp):
                    total_size += os.path.getsize(fp)
    except FileNotFoundError:
        return 0
    return total_size / (1024 * 1024)

# Clear cache files
def clear_cache_data(cache_path='./f1_cache'):
    if not os.path.exists(cache_path):
        return False
    success_count = 0
    year_pattern = re.compile(r"^\d{4}$")

    try:
        for item in os.listdir(cache_path):
            item_path = os.path.join(cache_path, item)
            
            if os.path.isdir(item_path) and year_pattern.match(item):
                try:
                    shutil.rmtree(item_path, onerror=remove_readonly)
                    success_count += 1
                except Exception as e:
                    st.warning(f"Impossible de supprimer le dossier {item} (utilisé par le système).")
        
        return success_count > 0
    except Exception as e:
        st.error(f"Erreur lors du parcours du cache : {e}")
        return False

# Clear files readonly
def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)