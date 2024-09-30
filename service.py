from flask import Flask, redirect, url_for, render_template, request, flash, jsonify
import sqlite3
from datetime import datetime
from main import conn, cursor

def check_scores(fighter1, score1, score2, fighter2):
    if score1 > score2:
        cursor.execute('''
                    UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?
                ''', (fighter1,))
        cursor.execute('''
                    UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?
                ''', (fighter2,))
    elif score2 > score1:
        cursor.execute('''
                    UPDATE FIGHTERS SET WINS = WINS + 1 WHERE NAME = ?
                ''', (fighter2,))
        cursor.execute('''
                    UPDATE FIGHTERS SET LOSES = LOSES + 1 WHERE NAME = ?
                ''', (fighter1,))

    return jsonify(success=True)

conn.commit()