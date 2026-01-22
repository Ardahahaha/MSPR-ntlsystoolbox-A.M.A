import os
import sys

# Configuration des couleurs ANSI
class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_logo():
    # Logo NTL stylisé avec dégradé simulé
    print(f"{Color.DARKCYAN}╔══════════════════════════════════════════════════════════════════╗{Color.END}")
    print(f"{Color.DARKCYAN}║ {Color.CYAN}███╗   ██╗████████╗██╗      {Color.PURPLE}--- SYS TOOLBOX ---{Color.DARKCYAN}           ║{Color.END}")
    print(f"{Color.DARKCYAN}║ {Color.CYAN}████╗  ██║╚══██╔══╝██║      {Color.END}Diagnostic / Backup / Audit    {Color.DARKCYAN}║{Color.END}")
    print(f"{Color.DARKCYAN}║ {Color.CYAN}██╔██╗ ██║   ██║   ██║      {Color.END}v1.0  | {Color.GREEN}● ONLINE{Color.DARKCYAN}             ║{Color.END}")
    print(f"{Color.DARKCYAN}║ {Color.CYAN}██║╚██╗██║   ██║   ██║                                     {Color.DARKCYAN}║{Color.END}")
    print(f"{Color.DARKCYAN}║ {Color.CYAN}██║ ╚████║   ██║   ███████╗ {Color.END}User: root@ntl-cli             {Color.DARKCYAN}║{Color.END}")
    print(f"{Color.DARKCYAN}║ {Color.CYAN}╚═╝  ╚═══╝   ╚═╝   ╚══════╝                                     {Color.DARKCYAN}║{Color.END}")
    print(f"{Color.DARKCYAN}╚══════════════════════════════════════════════════════════════════╝{Color.END}")
    print("")

def print_menu():
    # Cadre du menu avec dessins ASCII
    print(f" {Color.BOLD}MENU PRINCIPAL :{Color.END}")
    print(f" {Color.DARKCYAN}────────────────────────────────────────────────────────────────{Color.END}")
    
    # Item 1
    print(f" {Color.BLUE}┌──{Color.END} {Color.BOLD}[1]{Color.END} {Color.CYAN}INFRASTRUCTURE{Color.END}")
    print(f" {Color.BLUE}│{Color.END}   {Color.BLUE}⚡{Color.END}  Diagnostic complet (Ping, CPU, RAM)")
    print("")
    
    # Item 2
    print(f" {Color.PURPLE}┌──{Color.END} {Color.BOLD}[2]{Color.END} {Color.PURPLE}SAUVEGARDE WMS{Color.END}")
    print(f" {Color.PURPLE}│{Color.END}   {Color.PURPLE}💾{Color.END}  Export SQL & CSV")
    print("")

    # Item 3
    print(f" {Color.YELLOW}┌──{Color.END} {Color.BOLD}[3]{Color.END} {Color.YELLOW}AUDIT OBSOLESCENCE{Color.END}")
    print(f" {Color.YELLOW}│{Color.END}   {Color.YELLOW}☣ {Color.END}  Vérification EOL + Rapport HTML")
    print(f" {Color.DARKCYAN}────────────────────────────────────────────────────────────────{Color.END}")
    
    # Quitter
    print(f" {Color.RED}[0] ✕ Quitter{Color.END}")
    print("")

def main():
    clear_screen()
    print_logo()
    print_menu()
    
    # Input stylisé
    choice = input(f"{Color.BOLD}{Color.CYAN}ntl-cli > {Color.END}")
    print(f"\nVous avez choisi : {choice}")

if __name__ == "__main__":
    main()
