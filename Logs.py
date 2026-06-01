import mysql.connector
from tkinter import *
from tkinter import ttk


# MYSQL

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Ersha@123",
    database="camera_monitor"
)

cursor = db.cursor()

cursor.execute(
    """
    SELECT
    id,
    event_time,
    status,
    video_type
    FROM detection_logs
    ORDER BY id DESC
    """
)

rows = cursor.fetchall()


# UI

root = Tk()

root.title(
    "Camera Logs"
)

root.geometry(
    "900x500"
)


table = ttk.Treeview(
    root
)

table["columns"] = (
    "ID",
    "Time",
    "Status",
    "Type"
)

table.column(
    "#0",
    width=0
)

table.column(
    "ID",
    width=80
)

table.column(
    "Time",
    width=250
)

table.column(
    "Status",
    width=150
)

table.column(
    "Type",
    width=200
)


table.heading(
    "ID",
    text="ID"
)

table.heading(
    "Time",
    text="Event Time"
)

table.heading(
    "Status",
    text="Status"
)

table.heading(
    "Type",
    text="Media Type"
)


for row in rows:

    table.insert(
        "",
        END,
        values=row
    )

table.pack(
    fill=BOTH,
    expand=True
)

root.mainloop()

cursor.close()

db.close()