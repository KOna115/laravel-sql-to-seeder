#!/usr/bin/env python
#
# sqllaseed.py
# A simple Python script to convert SQL INSERT statements to Laravel seeders
#
# Usage: - python sqllaseed.py <file.sql>
#               or with python in PATH: sqllaseed.py <file.sql>
#        - Enter the table names to convert (separated by commas)
#        - Enter the PHP class name for each table
#

import sqlparse
import sys
import os


#-----------------------#
#                       #
#   SQL parsing logic   #
#                       #
#-----------------------#

# Extract the column definitions from a CREATE TABLE statement
def extract_definitions(token_list):
    definitions = []
    tmp = []
    par_level = 0
    for token in token_list.flatten():
        if token.is_whitespace:
            continue
        elif token.match(sqlparse.tokens.Punctuation, '('):
            par_level += 1
            continue
        if token.match(sqlparse.tokens.Punctuation, ')'):
            if par_level == 0:
                break
            else:
                par_level += 1
        elif token.match(sqlparse.tokens.Punctuation, ','):
            if tmp:
                definitions.append(tmp)
            tmp = []
        else:
            tmp.append(token)
    if tmp:
        definitions.append(tmp)
    return definitions

# Extract the table name from a CREATE TABLE statement
def extract_table_name(token_list):
    for token in token_list:
        if isinstance(token, sqlparse.sql.Identifier):
            return token.get_name()
    return None

# Extract the table name from an INSERT statement
def extract_table_name_from_insert(token_list):
    for idx, token in enumerate(token_list):
        if token.ttype is None:
            if token.get_name() is not None:
                return token.get_name()


    return None

# Extract the columns and values from an INSERT statement
def extract_insert_values(token_list):
    columns = []
    values = []
    
    for idx, token in enumerate(token_list):
        if isinstance(token, sqlparse.sql.Function):
            data = token.value
            data = data.split("(")[1].split(")")[0]

            columns_txt = data.split(",")

            for idx, column in enumerate(columns_txt):
                corrected = column.strip()
                corrected = corrected.replace("`", "")
                corrected = corrected.replace(",", "")
                columns.append(str(corrected))



        if isinstance(token, sqlparse.sql.Values):

            data = token.value

            # Remove VALUE keyword
            data = data.replace("VALUES", "")

            data = data.split("),")

            for idx, row in enumerate(data):
                row = row.replace("(", "")
                row = row.replace(")", "")
                row = row.replace(";", "")
                row = row.strip()
                row = row.split(",")

                for idy, column in enumerate(row):
                    corrected = column.strip()
                    corrected = corrected.replace("`", "")
                    corrected = corrected.replace(",", "")
                    corrected = corrected.replace("'", "")
                    corrected = corrected.replace('"', "")
                    row[idy] = str(corrected)

                values.append(row)

    return {
        "table_name": extract_table_name_from_insert(token_list),
        "columns": columns,
        "values": values
    }

# Convert the values to a Laravel seeder
def as_laravel_seeder(phpClass, columns, values):
    seeder = f"{phpClass}::create([\n"
    for idx, value in enumerate(values):
        if len(columns) > idx:
            if value == "NULL":
                seeder += f"\t'{columns[idx]}' => null,\n"
                continue

            if (value == "1" or value == "0") and columns[idx].startswith("is_"):
                if value == "1":
                    seeder += f"\t'{columns[idx]}' => true,\n"
                else:
                    seeder += f"\t'{columns[idx]}' => false,\n"

                continue

            if columns[idx].endswith("_id"):
                seeder += f"\t'{columns[idx]}' => {int(value)},\n"
                continue

            seeder += f"\t'{columns[idx]}' => '{value}',\n"

    seeder += "]);\n\n"
    return seeder




#-----------------------#
#                       #
#   Custom draw logic   #
#                       #
#-----------------------#

def print_separator():
    terminalWidth = os.get_terminal_size().columns
    print('-' * terminalWidth)

def print_text_centered(text):
    terminalWidth = os.get_terminal_size().columns
    print(" " * ((terminalWidth - len(str(text))) // 2) + str(text))

def print_tabulated_text(text_left, text_right):
    terminalWidth = os.get_terminal_size().columns
    print(f"{str(text_left)}{'.' * (terminalWidth - len(str(text_left)) - len(str(text_right)))}{str(text_right)}")



#-----------------------#
#                       #
#   Main running logic  #
#                       #
#-----------------------#
if __name__ == '__main__':
    SQL = ""

    file_name = sys.argv[1]

    if len(sys.argv) != 2:
        print("Usage: python sqllaseed.py <file.sql>")
        print("       or with python in PATH: sqllaseed.py <file.sql>")
        sys.exit(1)

    if not os.path.exists(file_name):
        print("File not found.")
        sys.exit(1)

    if not file_name.endswith(".sql"):
        print("Invalid file format. Please provide a .sql file.")
        sys.exit(1)
    
    with open(sys.argv[1], 'r', encoding="utf-8") as file:
        SQL = file.read()
        

    parsed = sqlparse.parse(SQL)
    tables = []
            
    for stmt in parsed:
        if stmt.get_type() != 'INSERT':
            continue

        table_name = extract_table_name_from_insert(stmt.tokens)

        tables.append(extract_insert_values(stmt.tokens))
    
    print_separator()
    print_text_centered("SQL Table Definitions")
    print_separator()
    for idx, table in enumerate(tables):
        print_tabulated_text(table["table_name"], idx)

    # Wait for console input
    convert_tables_txt = input("Enter the table names to convert (separated by commas): ")
    convert_tables = convert_tables_txt.split(",")

    print_separator()

    for idx, table in enumerate(tables):
        if table["table_name"] in convert_tables:
            print_separator()

            # Get default PHP class name
            defaultClassName = table["table_name"].capitalize()
            if defaultClassName.endswith("s"):
                defaultClassName = defaultClassName[:-1]
            
            if defaultClassName.endswith("ies"):
                defaultClassName = defaultClassName[:-3] + "y"
            
            # Check if user wants to change the PHP class name
            phpClassName = input(f"Enter the PHP class name for table \033[1m{table['table_name']}\033[0m: Default is \033[1m{defaultClassName}\033[0m (Press Enter to use default):")
            if phpClassName == "":
                phpClassName = defaultClassName

            print_separator()
            print_text_centered(f"Table: {table['table_name']} (PHP Class: {phpClassName})")
            print_separator()
            i = 0
            for column in table["columns"]:
                print_tabulated_text(column, i)
                i += 1

            print_separator()
            with open(f"{phpClassName}.php", "w", encoding="utf-8") as file:
                file.write(f"<?php\n\nuse App\\Models\\{phpClassName};\n\n")

                for idx, value in enumerate(table["values"]):
                    file.write(as_laravel_seeder(phpClassName, table["columns"], value))

                print_text_centered(f"File \033[1m{phpClassName}.php\033[0m created.")
                print_separator()
            
