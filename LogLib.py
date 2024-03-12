#!/usr/bin/env python
# coding: utf-8

# Auteur    : Patrick Pinard
# Date      : 
# Objet     : Logging 
# Source    : LogLib.py
# Version   : 1.0


#   Clavier MAC :      
#  {} = "alt/option" + "(" ou ")"
#  [] = "alt/option" + "5" ou "6"
#   ~  = "alt/option" + n    
#   \  = Alt + Maj + / 

# Importation des librairies nécessaires
import sys
import time
import logging
from Config_Parameters import DEBUG

DEBUG : True

# on récupère le fichier de log basic (défini au niveau Borg.py)
logging = logging.getLogger()

def log(message):
    if DEBUG:
        print(message)
    logging.info(message)

