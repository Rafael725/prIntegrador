import sqlite3
import tkinter as tk
from tkinter import simpledialog, messagebox, Toplevel, Listbox, filedialog
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import cv2
import os
import tkinter.ttk as ttk
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import tempfile
from PIL import Image
from reportlab.graphics.shapes import Drawing, Rect, String
from reportlab.graphics import renderPDF
from reportlab.lib import colors
# Crear una conexión a la base de datos
conn = sqlite3.connect('atletas.db')

# Crear un cursor
c = conn.cursor()
def obtener_id_serie_pruebas(atleta):
    # Consultar el número de series de pruebas registradas para este atleta
    c.execute("SELECT COUNT(DISTINCT id_serie_pruebas) FROM resultados_pruebas WHERE id_atleta = ?",
              (atleta["id"],))
    serie_count = c.fetchone()[0]
    return serie_count + 1  # Devolver el próximo identificador de serie


class RegistroAtletaDialog(simpledialog.Dialog):
    def body(self, master):
        tk.Label(master, text="Nombre:").grid(row=0)
        tk.Label(master, text="Edad:").grid(row=1)
        tk.Label(master, text="Peso (kg):").grid(row=2)
        tk.Label(master, text="Altura (cm):").grid(row=3)
        tk.Label(master, text="Deporte que practica:").grid(row=4)

        self.e1 = tk.Entry(master)
        self.e2 = tk.Entry(master)
        self.e3 = tk.Entry(master)
        self.e4 = tk.Entry(master)
        self.e5 = tk.Entry(master)

        self.e1.grid(row=0, column=1)
        self.e2.grid(row=1, column=1)
        self.e3.grid(row=2, column=1)
        self.e4.grid(row=3, column=1)
        self.e5.grid(row=4, column=1)

        return self.e1  # initial focus

    def apply(self):
        nombre = self.e1.get()
        edad = int(self.e2.get())
        peso = float(self.e3.get())
        altura = int(self.e4.get())
        deporte = self.e5.get()

        # Agregar el atleta a la base de datos
        c.execute("INSERT INTO atletas VALUES (:nombre, :edad, :peso, :altura, :deporte)",
                  {'nombre': nombre, 'edad': edad, 'peso': peso, 'altura': altura, 'deporte': deporte})

          # Obtener el id del atleta recién insertado
        atleta_id = c.lastrowid

        # Guardar (commit) los cambios
        conn.commit()

        # Devolver el diccionario del atleta con el id
        return {"id": atleta_id, "nombre": nombre, "edad": edad, "peso": peso, "altura": altura, "deporte": deporte}

class DetallesAtletaDialog(simpledialog.Dialog):
    def __init__(self, parent, atleta):
        self.atleta = atleta
        super().__init__(parent)

    def body(self, master):
        tk.Label(master, text=self.atleta["nombre"], font=("Helvetica", 20)).grid(row=0)
        tk.Label(master, text=f"Edad: {self.atleta['edad']}").grid(row=1)
        tk.Label(master, text=f"Peso: {self.atleta['peso']} kg").grid(row=2)
        tk.Label(master, text=f"Altura: {self.atleta['altura']} cm").grid(row=3)
        tk.Label(master, text=f"Deporte: {self.atleta['deporte']}").grid(row=4)

        tk.Button(master, text="Volver al menú principal", command=self.volver).grid(row=5)
        tk.Button(master, text="Cargar pruebas físicas", command=self.cargar_pruebas).grid(row=6)
        


    def volver(self):
        self.destroy()
        root.deiconify()

    def cargar_pruebas(self):
        self.destroy()
        PruebasFisicasDialog(root, self.atleta)

class PruebasFisicasDialog(simpledialog.Dialog):
    def __init__(self, parent, atleta):
        self.atleta = atleta
        super().__init__(parent)
        self.bind("<Destroy>", self.on_destroy)

    def on_destroy(self, event):
        # Eliminar cualquier evento asociado a la ventana antes de destruirla
        self.unbind("<Destroy>")
    def __init__(self, parent, atleta):
        self.atleta = atleta
        super().__init__(parent)

    def body(self, master):
        tk.Label(master, text="Pruebas Físicas", font=("Helvetica", 20)).grid(row=0)

        tk.Button(master, text="Salto vertical", command=self.salto_vertical).grid(row=1)
        tk.Button(master, text="Prueba de equilibrio", command=self.prueba_equilibrio).grid(row=2)
        tk.Button(master, text="Eyetracker", command=self.eyetracker).grid(row=3)
        tk.Button(master, text="Blazepods", command=self.blazepods).grid(row=4)

    def salto_vertical(self):
        self.destroy()
        SaltoVerticalDialog(root, self.atleta)

    def prueba_equilibrio(self):
        self.destroy()
        PruebaEquilibrioDialog(root, self.atleta)
        

    def eyetracker(self):
        self.destroy()
        EyetrackerDialog(root, self.atleta)
        

    def blazepods(self):
        self.destroy()
        PruebaBlazepodsDialog(root, self.atleta)

class SaltoVerticalDialog(simpledialog.Dialog):
    def __init__(self, parent, atleta):
        self.atleta = atleta
        self.id_serie_pruebas = obtener_id_serie_pruebas(atleta)  # Definir el ID de la serie de pruebas
        self.id_prueba=1
        self.saltos = []
        self.loaded_label = None
        self.inputs_inicio_vuelo = []
        self.inputs_fin_vuelo = []
        self.inputs_inicio_impulso = []
        self.inputs_fin_impulso = []
        self.graficas_window = None  # Para guardar la referencia a la ventana de las gráficas
        super().__init__(parent)
        
    def body(self, master):
        tk.Label(master, text="Salto Vertical", font=("Helvetica", 20)).pack()

        self.loaded_label = tk.Label(master, text="", fg="green")
        self.loaded_label.pack()

        tk.Button(master, text="Cargar Salto 1", command=lambda: self.cargar_salto(0)).pack()
        tk.Button(master, text="Cargar Salto 2", command=lambda: self.cargar_salto(1)).pack()
        tk.Button(master, text="Cargar Salto 3", command=lambda: self.cargar_salto(2)).pack()

        tk.Button(master, text="Graficar", command=lambda: self.graficar(master)).pack()

        self.figures = []

    def cargar_salto(self, i):
        filename = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx;*.xls")])
        if filename:
            df = pd.read_excel(filename, header=None)
            tiempo = df.iloc[9:1208, 0]  # Columna 'A' en Excel, índice 0 en pandas
            fuerza_z = df.iloc[9:1208, 3]  # Columna 'D' en Excel, índice 3 en pandas
            self.saltos.append((tiempo, fuerza_z))
            self.loaded_label.config(text=f"Archivo {i+1} cargado correctamente")

    def graficar(self, master):
        if len(self.saltos) != 3:
            messagebox.showerror("Error", "Por favor, carga los tres saltos antes de graficar.")
            return

        self.graficas_window = tk.Toplevel(master)
        self.graficas_window.title("Gráficas")
        self.graficas_window.protocol("WM_DELETE_WINDOW", self.cerrar_ventana_graficas)  # Manejar el cierre de la ventana ################
    
        fig, axs = plt.subplots(3, 1, figsize=(8, 18))
        
        for i, (tiempo, fuerza_z) in enumerate(self.saltos):
            axs[i].plot(tiempo, fuerza_z)
            axs[i].set_xlabel('Tiempo')
            axs[i].set_ylabel('Fuerza en Z')
            
            # Añadir inputs de inicio y fin de vuelo, y de impulso
            frame = tk.Frame(self.graficas_window)
            frame.pack(side=tk.LEFT, padx=20)
            
            tk.Label(frame, text=f"Salto {i+1}").pack()
            
            tk.Label(frame, text="Inicio de Vuelo:").pack()
            input_inicio_vuelo = tk.Entry(frame)
            input_inicio_vuelo.pack()
            self.inputs_inicio_vuelo.append(input_inicio_vuelo)
            
            tk.Label(frame, text="Fin de Vuelo:").pack()
            input_fin_vuelo = tk.Entry(frame)
            input_fin_vuelo.pack()
            self.inputs_fin_vuelo.append(input_fin_vuelo)
            
            tk.Label(frame, text="Inicio de Impulso:").pack()
            input_inicio_impulso = tk.Entry(frame)
            input_inicio_impulso.pack()
            self.inputs_inicio_impulso.append(input_inicio_impulso)
            
            tk.Label(frame, text="Fin de Impulso:").pack()
            input_fin_impulso = tk.Entry(frame)
            input_fin_impulso.pack()
            self.inputs_fin_impulso.append(input_fin_impulso)

            # Función para mostrar las coordenadas al hacer clic
            def on_click(event):
                x, y = event.xdata, event.ydata
                if x is not None and y is not None:
                    messagebox.showinfo("Coordenadas", f"Coordenada clic: ({x:.2f}, {y:.2f})")
                
            axs[i].figure.canvas.mpl_connect('button_press_event', on_click)
        tk.Button(master, text="Calcular", command=self.guardar_resultados).pack() # Botón para calcular altura e impulso

        plt.show(block=False)  # Mostrar las gráficas sin bloquear la ejecución del código
    def cerrar_ventana_graficas(self):
            if self.graficas_window is not None:
                print("Cerrando ventana de las gráficas...")
                self.graficas_window.destroy()
                plt.close('all')
                self.graficas_window = None
            self.destroy() 
    def guardar_resultados(self):
        alturas = []
        impulsos = []
        
        for i in range(3):
            inicio_vuelo = float(self.inputs_inicio_vuelo[i].get( ))
            fin_vuelo = float(self.inputs_fin_vuelo[i].get())
            inicio_impulso = float(self.inputs_inicio_impulso[i].get())
            fin_impulso = float(self.inputs_fin_impulso[i].get())

            # Calcular altura
            altura = 9.81 * ((fin_vuelo - inicio_vuelo) ** 2) / 8
            print(f"Altura para salto {i+1}: {altura}")
            alturas.append(altura)  # Agregar altura al vector

            # Calcular impulso
            tiempo, fuerza_z = self.saltos[i]
            tiempo = pd.to_numeric(tiempo, errors='coerce')
            inicio_impulso_index = tiempo[9:1208].sub(inicio_impulso).abs().idxmin() - 9
            fin_impulso_index = tiempo[9:1208].sub(fin_impulso).abs().idxmin() - 9
            impulso_total = fuerza_z.iloc[inicio_impulso_index:fin_impulso_index].sum()
            print(f"Impulso total para salto {i+1}: {impulso_total}")
            
            impulsos.append(impulso_total)

        # Cierra la ventana de las gráficas
        self.cerrar_ventana_graficas()
        # Calcular promedios
        altura_promedio = ((sum(alturas))*100) / (len(alturas))
        impulso_promedio = (sum(impulsos) / len(impulsos))

        print(f"Altura Promedio: {altura_promedio}")
        print(f"Impulso Promedio: {impulso_promedio}")

        # Guardar en la base de datos con el ID de serie de pruebas asociado
        self.guardar_promedios_en_bd(self.atleta["id"], altura_promedio, impulso_promedio, self.id_serie_pruebas,self.id_prueba)

        # Comprueba si self.master existe y está visible antes de intentar crear PruebasFisicasDialog
        if self.master is not None and self.master.winfo_exists():
            # Muestra el menú de las 4 pruebas
            PruebasFisicasDialog(self.master, self.atleta)
            self.master.destroy()  # Si es necesario destruir la ventana actual
    def guardar_promedios_en_bd(self, atleta_id, altura_promedio, impulso_promedio, id_serie_pruebas,id_prueba):
        fecha_prueba = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Obtener la fecha y hora actual
        c.execute("INSERT INTO resultados_pruebas (id_atleta, id_prueba,prueba, altura_promedio,impulso_promedio, id_serie_pruebas,fecha_prueba) VALUES (?, ?, ?, ?,?,?,?)",
                (atleta_id,id_prueba, "Salto Vertical", altura_promedio,impulso_promedio, id_serie_pruebas,fecha_prueba))
        conn.commit()

        
class EyetrackerDialog(Toplevel):
    def __init__(self, master,atleta):
        self.id_prueba=2
        super().__init__(master)
        self.title("Eyetracker")
        self.atleta = atleta
        self.video_loaded = False  # Agregar el atributo video_loaded
        self.id_serie_pruebas = obtener_id_serie_pruebas(atleta)  # Definir el ID de la serie de pruebas al inicializar el diálogo

        # Etiqueta grande con el texto "Eyetracker"
        label = tk.Label(self, text="Eyetracker", font=("Helvetica", 20))
        label.pack(pady=20)

        # Botón para cargar video
        btn_cargar_video = tk.Button(self, text="Cargar video", command=self.cargar_video)
        btn_cargar_video.pack(pady=10)

        # Botón para calcular
        btn_calcular = tk.Button(self, text="Calcular", command=self.calcular)
        btn_calcular.pack(pady=10)

    def cargar_video(self):
        video_path = filedialog.askopenfilename(filetypes=[("Video files", "*.mp4;*.avi")])
        if video_path:
            self.video_path = video_path
            self.loaded_label = tk.Label(self, text="Video cargado correctamente", fg="green")
            self.loaded_label.pack()
            self.video_loaded = True  # Configurar video_loaded como True cuando se carga un video

    def calcular(self):
        if not self.video_loaded or not self.atleta:
            messagebox.showerror("Error", "Por favor, carga un video antes de calcular.")
            return
        
        cap = cv2.VideoCapture(self.video_path)
        green_lower = (35, 100, 100)
        green_upper = (85, 255, 255)
        white_lower = (0, 0, 200)
        white_upper = (180, 50, 255)
        green_x = []
        green_y = []
        white_x = []
        white_y = []

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            green_mask = cv2.inRange(hsv, np.array(green_lower), np.array(green_upper))
            white_mask = cv2.inRange(hsv, np.array(white_lower), np.array(white_upper))

            green_contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            white_contours, _ = cv2.findContours(white_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in green_contours:
                if cv2.contourArea(contour) > 10:
                    M = cv2.moments(contour)
                    green_x.append(int(M["m10"] / M["m00"]))
                    green_y.append(int(M["m01"] / M["m00"]))

            for contour in white_contours:
                if cv2.contourArea(contour) > 10:
                    M = cv2.moments(contour)
                    white_x.append(int(M["m10"] / M["m00"]))
                    white_y.append(int(M["m01"] / M["m00"]))

        cap.release()

        min_length = min(len(green_x), len(green_y), len(white_x), len(white_y))
        green_x = green_x[:min_length]
        green_y = green_y[:min_length]
        white_x = white_x[:min_length]
        white_y = white_y[:min_length]

        green_x = np.array(green_x)
        green_y = np.array(green_y)
        white_x = np.array(white_x)
        white_y = np.array(white_y)

        distances = np.sqrt((green_x - white_x)**2 + (green_y - white_y)**2)

        mean_distance = np.mean(distances)
        std_distance = np.std(distances)
        max_distance = np.max(distances)
        # Obtener el ID de serie de pruebas al inicializar el diálogo
        id_serie_pruebas = obtener_id_serie_pruebas(self.atleta)
       # Guardar en la base de datos
        self.guardar_resultados_en_bd(self.atleta["id"], mean_distance, std_distance, max_distance, id_serie_pruebas,self.id_prueba)


        messagebox.showinfo("Cálculo", f"Distancia Promedio: {mean_distance}\nDesviación Estándar de la Distancia: {std_distance}\nDistancia Máxima: {max_distance}")
        self.destroy()
        # Muestra el menú de las 4 pruebas
        PruebasFisicasDialog(self.master, self.atleta)
    def guardar_resultados_en_bd(self, atleta_id, mean_distance, std_distance, max_distance, id_serie_pruebas,id_prueba):
        fecha_prueba = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Obtener la fecha y hora actual
    
        c.execute("INSERT INTO resultados_pruebas (id_atleta,id_prueba, prueba, mean_distance, std_distance, max_distance, id_serie_pruebas,fecha_prueba) VALUES (?,?, ?, ?, ?, ?, ?,?)",
                (atleta_id,id_prueba, "Eyetracker", mean_distance, std_distance, max_distance, id_serie_pruebas,fecha_prueba))
        conn.commit()


class PruebaEquilibrioDialog(simpledialog.Dialog):
    def __init__(self, parent, atleta):
        self.atleta = atleta
        self.id_prueba=3
        super().__init__(parent)
        
    def cancel(self):
        # Llamar a la clase PruebasFisicasDialog al cerrar la ventana
        PruebasFisicasDialog(self.master, self.atleta)
        self.destroy()
    def body(self, master):
        tk.Label(master, text="Prueba de Equilibrio", font=("Helvetica", 20)).grid(row=0)

        tk.Label(master, text="Pierna Izquierda", font=("Helvetica", 16)).grid(row=1, column=0, sticky='w')
        tk.Label(master, text="Área:").grid(row=2, column=0, sticky='w')
        self.entry_area_izquierda = tk.Entry(master)
        self.entry_area_izquierda.grid(row=2, column=1)
        tk.Label(master, text="Veces que bajó el pie:").grid(row=3, column=0, sticky='w')
        self.entry_veces_izquierda = tk.Entry(master)
        self.entry_veces_izquierda.grid(row=3, column=1)

        tk.Label(master, text="Pierna Derecha", font=("Helvetica", 16)).grid(row=4, column=0, sticky='w')
        tk.Label(master, text="Área:").grid(row=5, column=0, sticky='w')
        self.entry_area_derecha = tk.Entry(master)
        self.entry_area_derecha.grid(row=5, column=1)
        tk.Label(master, text="Veces que bajó el pie:").grid(row=6, column=0, sticky='w')
        self.entry_veces_derecha = tk.Entry(master)
        self.entry_veces_derecha.grid(row=6, column=1)

        tk.Button(master, text="Cargar Resultados", command=self.guardar_resultados).grid(row=7, column=0, pady=10)
        tk.Button(master, text="Cerrar", command=self.cancel).grid(row=7, column=1, pady=10)

    def guardar_resultados(self):
        # Obtener los valores de los campos de entrada
        area_izquierda = self.entry_area_izquierda.get()
        veces_izquierda = self.entry_veces_izquierda.get()
        area_derecha = self.entry_area_derecha.get()
        veces_derecha = self.entry_veces_derecha.get()

        # Obtener el ID de serie de pruebas al inicializar el diálogo
        id_serie_pruebas = obtener_id_serie_pruebas(self.atleta)

        # Definir los resultados a guardar
        resultados = [
            ("Equilibrio: Área Pierna Izquierda", area_izquierda),
            ("Equilibrio: Veces que bajó el pie Izquierda", veces_izquierda),
            ("Equilibrio: Área Pierna Derecha", area_derecha),
            ("Equilibrio: Veces que bajó el pie Derecha", veces_derecha)
        ]

     # Guardar los resultados en la base de datos
        self.guardar_resultados_en_bd(self.atleta["id"], area_izquierda, veces_izquierda, area_derecha, veces_derecha, id_serie_pruebas,self.id_prueba)
        messagebox.showinfo("Carga de Resultados", "Resultados cargados exitosamente.")

    def guardar_resultados_en_bd(self, atleta_id, area_izquierda, veces_izquierda, area_derecha, veces_derecha, id_serie_pruebas,id_prueba):
        fecha_prueba = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Obtener la fecha y hora actual
    
        c.execute("INSERT INTO resultados_pruebas (id_atleta, id_prueba, prueba, area_izquierda, veces_izquierda, area_derecha, veces_derecha, id_serie_pruebas,fecha_prueba) VALUES (?,?,?, ?, ?, ?, ?, ?,?)",
                    (atleta_id,id_prueba,"Prueba de equilibrio", area_izquierda, veces_izquierda, area_derecha, veces_derecha, id_serie_pruebas,fecha_prueba))
        conn.commit()



    def cancel(self):
        # Llamar a la clase PruebasFisicasDialog al cerrar la ventana
        self.destroy()
        PruebasFisicasDialog(self.master, self.atleta)
class PruebaBlazepodsDialog(simpledialog.Dialog):
    def __init__(self, parent, atleta):
        self.atleta = atleta
        self.id_prueba=4
        super().__init__(parent)

    def body(self, master):
        tk.Label(master, text="Prueba de Blazepods", font=("Helvetica", 20)).grid(row=0)

        tk.Label(master, text="Número de Hits:").grid(row=1)
        tk.Label(master, text="Tiempo de Reacción:").grid(row=2)

        self.hits_entry = tk.Entry(master)
        self.hits_entry.grid(row=1, column=1)
        self.reaccion_entry = tk.Entry(master)
        self.reaccion_entry.grid(row=2, column=1)

        tk.Button(master, text="Cargar resultados", command=self.guardar_resultados).grid(row=3, columnspan=2)
        tk.Button(master, text="Cerrar", command=self.cancel).grid(row=4, columnspan=2)

    def guardar_resultados(self):
        hits = self.hits_entry.get()
        reaccion = self.reaccion_entry.get()

       # Obtener el ID de serie de pruebas al inicializar el diálogo
        id_serie_pruebas = obtener_id_serie_pruebas(self.atleta)

        # Guardar los resultados en la base de datos con el ID de serie de pruebas
        self.guardar_resultados_en_bd(self.atleta["id"], hits, reaccion, id_serie_pruebas,self.id_prueba)


        print("Resultados de la prueba de Blazepods:")
        print(f"Número de Hits: {hits}")
        print(f"Tiempo de Reacción: {reaccion}")
        messagebox.showinfo("Carga de Resultados", "Resultados cargados exitosamente.")

    def guardar_resultados_en_bd(self, atleta_id, hits, reaccion, id_serie_pruebas,id_prueba):
        fecha_prueba = datetime.now().strftime("%Y-%m-%d %H:%M:%S")  # Obtener la fecha y hora actual
        c.execute("INSERT INTO resultados_pruebas (id_atleta,id_prueba,prueba, hits, reaccion, id_serie_pruebas,fecha_prueba) VALUES (?,?, ?, ?, ?,?,?)",
                (atleta_id,id_prueba,"Blazepods", hits, reaccion, id_serie_pruebas,fecha_prueba))
        conn.commit()


    def cancel(self):
        # Llamar a la clase PruebasFisicasDialog al cerrar la ventana
        self.destroy()
        PruebasFisicasDialog(self.master, self.atleta)
class GeneradorReportes(simpledialog.Dialog):
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Generador de Reportes")
        self.root.geometry("300x200")
        
        self.label_atleta = tk.Label(self.root, text="Seleccione un atleta:")
        self.label_atleta.pack(pady=5)
        
        self.atletas_combobox = ttk.Combobox(self.root)
        self.atletas_combobox.pack(pady=5)
        self.btn_seleccionar_reporte = tk.Button(self.root, text="Seleccionar Tipo de Reporte", command=self.mostrar_menu_reporte)
        self.btn_seleccionar_reporte.pack(pady=10)
        
        self.cargar_atletas()
    def agrupar_pruebas(self, id_atleta):
        grupos_pruebas = []
        # Realizar la consulta para obtener los resultados del atleta especificado
        c.execute("SELECT * FROM resultados_pruebas WHERE id_atleta = ?", (id_atleta,))
        resultados = c.fetchall()

        # Diccionarios para agrupar resultados por tipo de prueba
        eyetracker = []
        blazepods = []
        salto = []
        equilibrio = []

        # Agrupar los resultados por el id_serie_prueba (índice 2)
        for resultado in resultados:
            id_serie_prueba = resultado[16]
            if id_serie_prueba == 2:
                eyetracker.append(resultado)
            elif id_serie_prueba == 4:
                blazepods.append(resultado)
            elif id_serie_prueba == 1:
                salto.append(resultado)
            elif id_serie_prueba == 3:
                equilibrio.append(resultado)

        # Ordenar los registros dentro de cada prueba por algún criterio específico (e.g., fecha o ID)
        eyetracker.sort(key=lambda x: x[0])  # Suponiendo que la fecha o ID es el primer campo
        blazepods.sort(key=lambda x: x[0])
        salto.sort(key=lambda x: x[0])
        equilibrio.sort(key=lambda x: x[0])

        # Agrupar los resultados en grupos de 4 (uno de cada tipo)
        for i in range(max(len(eyetracker), len(blazepods), len(salto), len(equilibrio))):
            grupo = []
            if i < len(eyetracker):
                grupo.append(eyetracker[i])
            if i < len(blazepods):
                grupo.append(blazepods[i])
            if i < len(salto):
                grupo.append(salto[i])
            if i < len(equilibrio):
                grupo.append(equilibrio[i])
            grupos_pruebas.append(grupo)
    

        return grupos_pruebas
    def cargar_atletas(self):
        c.execute("SELECT nombre FROM atletas")
        atletas = c.fetchall()
        nombres_atletas = [atleta[0] for atleta in atletas]
        self.atletas_combobox['values'] = nombres_atletas
    def mostrar_menu_reporte(self):
        atleta_seleccionado = self.atletas_combobox.get()
        if atleta_seleccionado:
            # Buscar el id_atleta en la tabla de resultados_pruebas basado en el nombre del atleta
            c.execute("""
                SELECT rp.id_atleta
                FROM resultados_pruebas rp
                JOIN atletas a ON rp.id_atleta = a.id
                WHERE a.nombre = ?
                """, (atleta_seleccionado,))
            resultado = c.fetchone()
            if resultado:
                id_atleta = resultado[0]
                menu = tk.Toplevel()
                menu.title("Seleccionar Tipo de Reporte")
                
                label_titulo = tk.Label(menu, text="Seleccione el tipo de reporte:")
                label_titulo.pack(pady=5)

                btn_reporte_individual = tk.Button(menu, text="Reporte Individual", command=lambda: self.generar_reporte_individual(id_atleta))
                btn_reporte_individual.pack(pady=5)

                btn_reporte_comparativo = tk.Button(menu, text="Reporte Comparativo", command=lambda: self.mostrar_seleccion_comparativo(id_atleta))
                btn_reporte_comparativo.pack(pady=5)
            else:
                messagebox.showerror("Error", "No se encontró el atleta en la base de datos.")
        else:
            messagebox.showerror("Error", "Por favor, seleccione un atleta.")
    
    def mostrar_seleccion_comparativo(self, id_atleta1):
        # Obtener los grupos de pruebas del atleta
        grupos_pruebas = self.agrupar_pruebas(id_atleta1)
        
        # Mostrar un diálogo para seleccionar los dos grupos de pruebas
        seleccion_dialog = SeleccionarGruposPruebasDialog(self.root, grupos_pruebas)
        self.root.wait_window(seleccion_dialog.top)

        grupo_seleccionado1, grupo_seleccionado2 = seleccion_dialog.resultado

        if grupo_seleccionado1 and grupo_seleccionado2:
            pdf_name = "reporte_comparativo.pdf"
            logo_path=r"C:\Users\Rafa\Documents\Tec mty\BLOQUE INTEGRADOOOR\programación beta\15Abr2024\logo.jpg"
            self.generar_reporte_comparativo(grupo_seleccionado1, grupo_seleccionado2, pdf_name, id_atleta1, logo_path)
        else:
            messagebox.showerror("Error", "Debe seleccionar dos grupos de pruebas.")

    def generar_reporte_individual(self, id_atleta):
        grupos_pruebas = self.agrupar_pruebas(id_atleta)
      #  for i, grupo in enumerate(grupos_pruebas, start=1):
       #     print(f"Grupo {i}: {grupo}")
        # Mostrar un menú para que el usuario seleccione el grupo de pruebas
        menu = tk.Toplevel()
        menu.title("Seleccionar Grupo")
        
        label = tk.Label(menu, text="Seleccione el número del grupo de pruebas:")
        label.pack(pady=5)
        
        # Crear un Listbox para mostrar las opciones de grupo
        listbox = tk.Listbox(menu)
        listbox.pack(pady=5)
        
        # Llenar el Listbox con las opciones de grupo
        for i, grupo in enumerate(grupos_pruebas, start=1):
            listbox.insert(tk.END, f"Grupo {i}")
        
        # Función para manejar la selección del usuario
        def on_select():
            # Obtener el índice seleccionado
            index = listbox.curselection()
            if index:
               # Obtener el grupo seleccionado
                seleccion = int(index[0])
                grupo_seleccionado = grupos_pruebas[seleccion]
                logo_path=r"C:\Users\Rafa\Documents\Tec mty\BLOQUE INTEGRADOOOR\programación beta\15Abr2024\logo.jpg"

                # Crear una nueva figura para mostrar las gráficas
                pdf_name = f"rep_INDI_grupo_{seleccion + 1}.pdf"
                self.crear_pdf_reporte(grupo_seleccionado,pdf_name,id_atleta,logo_path)
                messagebox.showinfo("Reporte Generado", f"El reporte ha sido generado y guardado como {pdf_name}")
            else:
                messagebox.showwarning("Selección inválida", "Por favor, seleccione un grupo.")
        # Botón para confirmar la selección
        btn_seleccionar = tk.Button(menu, text="Seleccionar", command=on_select)
        btn_seleccionar.pack(pady=5)
    def calcular_progreso_inicial_bp(self,resultado1, resultado2):
        # Aquí debes definir cómo calcular el progreso inicial de acuerdo a las métricas que tengas.
        # Para el ejemplo, vamos a asumir que queremos mejorar ciertas métricas en un 70%
        progreso_inicial_hits = (resultado2[13] - resultado1[13]) / resultado1[13] * 100
        progreso_inicial_reaccion = (resultado2[14] - resultado1[14]) / resultado1[14] * 100
        progreso_promedio_bp=(progreso_inicial_hits+progreso_inicial_reaccion)/2
        return progreso_promedio_bp
    def calcular_progreso_inicial_salto(self, resultado1, resultado2):
        progreso_altura = ((resultado2[4] - resultado1[4]) / resultado1[4]) * 100
        progreso_impulso = ((resultado2[5] - resultado1[5]) / resultado1[5]) * 100
        progreso_salto=(progreso_altura+progreso_impulso)/2
        return progreso_salto
    def calcular_progreso_inicial_equilibrio(self, resultado1, resultado2):
        # Calcular el progreso para Área Izquierda y Área Derecha (se espera que aumenten)
        progreso_area_izquierda = ((resultado2[9] - resultado1[9]) / resultado1[9]) * 100 if resultado1[9] != 0 else 0
        progreso_area_derecha = ((resultado2[11] - resultado1[11]) / resultado1[11]) * 100 if resultado1[11] != 0 else 0

        # Calcular el progreso para Veces Izquierda y Veces Derecha (se espera que disminuyan)
        progreso_veces_izquierda = ((resultado1[10] - resultado2[10]) / resultado1[10]) * 100 if resultado1[10] != 0 else -resultado2[10] * 100
        progreso_veces_derecha = ((resultado1[12] - resultado2[12]) / resultado1[12]) * 100 if resultado1[12] != 0 else -resultado2[12] * 100

        # Promediar el progreso de las áreas
        progreso_area_promedio = (progreso_area_izquierda + progreso_area_derecha) / 2
        progreso_veces_promedio=(progreso_veces_derecha+progreso_veces_izquierda)/2
        progreso_promedio_eq=(progreso_area_promedio+progreso_veces_promedio)/2

        return progreso_promedio_eq
    def calcular_progreso_inicial_eyetracker(self, resultado1, resultado2):
        # Datos del resultado 1 (valores iniciales)
        distancia_promedio_inicial = resultado1[6]
        desviacion_estandar_inicial = resultado1[7]
        distancia_maxima_inicial = resultado1[8]
        
        # Datos del resultado 2 (valores actuales)
        distancia_promedio_actual = resultado2[6]
        desviacion_estandar_actual = resultado2[7]
        distancia_maxima_actual = resultado2[8]

        # Calcular progreso (disminución representa mejora)
        progreso_distancia_promedio =100- ((distancia_promedio_actual *100)/ distancia_promedio_inicial)
        progreso_desviacion_estandar =100- ((desviacion_estandar_actual *100)/ desviacion_estandar_inicial) 
        progreso_distancia_maxima =100- ((distancia_maxima_actual*100) / distancia_maxima_inicial)

        # Tomar el promedio de los progresos de cada métrica
        progreso_promedio_et = (progreso_distancia_promedio + progreso_desviacion_estandar + progreso_distancia_maxima) / 3
        print(progreso_promedio_et)
        
        return progreso_promedio_et

    def generar_reporte_comparativo(self, grupo_seleccionado1, grupo_seleccionado2, pdf_name, id_atleta1,logo_path):
        logo_path=r"C:\Users\Rafa\Documents\Tec mty\BLOQUE INTEGRADOOOR\programación beta\15Abr2024\logo.jpg"
        # Obtener los detalles del atleta 1
        atleta_details1 = self.obtener_detalles_atleta(id_atleta1)
        # Obtener la ruta completa del directorio de descargas
        downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
        # Crear un archivo temporal para almacenar las gráficas
        pdf_path = os.path.join(downloads_dir, pdf_name)
        c = canvas.Canvas(pdf_path, pagesize=letter)
        width, height = letter
        margin = 50
        items_per_page = 2
        item_count = 0
        # Dibujar el logotipo de la marca en todas las páginas
        self.dibujar_logotipo(c, logo_path, width, height, margin)
        # Dibujar los detalles del atleta 1 en la primera página
        self.dibujar_datos_atleta(c, atleta_details1, width, height)
        meta_progreso = 70  # Meta de progreso deseado
       # self.dibujar_datos_atleta(c, atleta_details, width, height) ESTA ES LA MISMA Q LA OTRA FUN

        y_position = height - margin

        for resultado1, resultado2 in zip(grupo_seleccionado1, grupo_seleccionado2):
            id_serie_prueba1 = resultado1[16]
            id_serie_prueba2 = resultado2[16]
            if id_serie_prueba1 == id_serie_prueba2:
                datos_validos1 = []
                datos_validos2 = []
                titulo = ""
                if id_serie_prueba1 == 2:  # Eyetracker
                    titulo = "Resultados Eyetracker"
                    datos_validos1 = [
                        ("Distancia promedio", resultado1[6]),
                        ("Desviación estándar", resultado1[7]),
                        ("Distancia máxima", resultado1[8])
                    ]
                    datos_validos2 = [
                        ("Distancia promedio", resultado2[6]),
                        ("Desviación estándar", resultado2[7]),
                        ("Distancia máxima", resultado2[8])
                    ]
                    item_count += 2
                    self.generar_grafica_comparativa_eyetracker(resultado1, resultado2)
                    temp_plot_path = "grafica_comparativa_eyetracker.png"
                    # Insertar la gráfica en el PDF
                    c.drawImage(temp_plot_path, margin, y_position - 420, width  - 2 * margin, 200)
                    os.remove(temp_plot_path)  # Eliminar la imagen temporal
                    # Dibujar el título y los datos válidos en el PDF
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(margin, y_position - 110, titulo)
                    y_position -= 20

                    for dato1, dato2 in zip(datos_validos1, datos_validos2):
                        c.setFont("Helvetica", 12)
                        c.drawString(margin + 10, y_position - 120, f"{dato1[0]}: {dato1[1]} - {dato2[1]}")
                        y_position -= 30
                     # Calcular el progreso
                    progreso_promedio_et = self.calcular_progreso_inicial_eyetracker(resultado1, resultado2)

                    # Dibujar la barra de progreso para distancia promedio
                    meta=70
                    self.dibujar_barra_progreso_et(c, progreso_promedio_et, meta, margin, y_position - 590, width-2*margin, 20)
                    c.setFont("Helvetica", 12)
                    c.drawString(margin, y_position - 550, f"Progreso de Prueba de concentracion")

                elif id_serie_prueba1 == 1:  # Salto
                    # Dibujar el logotipo de la marca en todas las páginas
                    self.dibujar_logotipo(c, logo_path, width, height,margin)
                    titulo = "Resultados Salto"
                    datos_validos1 = [
                            ("Altura promedio", resultado1[4]),
                            ("Impulso promedio", resultado1[5])
                        ]
                    datos_validos2 = [
                            ("Altura promedio", resultado2[4]),
                            ("Impulso promedio", resultado2[5])
                        ]
                    item_count+=2
                    self.generar_graficas_comparativas_salto(resultado1, resultado2)
                    temp_plot_path_altura = "grafica_comparativa_altura_salto.png"
                    temp_plot_path_impulso = "grafica_comparativa_impulso_salto.png"
                     # Dibujar el título y los datos válidos en el PDF
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(margin, y_position - 50, titulo)
                   # y_position -= 220
                    # Insertar las gráficas en el PDF
                    c.drawImage(temp_plot_path_altura, margin, y_position - 300, width  - 2 * margin, 200)
                    c.drawImage(temp_plot_path_impulso, margin, y_position - 520, width  - 2 * margin, 200)
                    os.remove(temp_plot_path_altura)  # Eliminar la imagen temporal
                    os.remove(temp_plot_path_impulso)  # Eliminar la imagen temporal
                    progreso_salto = self.calcular_progreso_inicial_salto(resultado1, resultado2)
                    meta = 95

                   
                    for dato1, dato2 in zip(datos_validos1, datos_validos2):
                        c.setFont("Helvetica", 12)
                        c.drawString(margin , y_position - 550, f"{dato1[0]}: {dato1[1]} - {dato2[1]}")
                        y_position -= 30
                    self.dibujar_barra_progreso_salto(c, progreso_salto, meta, margin, y_position - 590, width - 2 * margin, 20)
                   
                    c.setFont("Helvetica", 12)
                    c.drawString(margin, y_position - 550, f"Progreso de Prueba de Salto")
                elif id_serie_prueba1 == 3:  # Equilibrio
                    self.dibujar_logotipo(c, logo_path, width, height,margin)
                    titulo = "Resultados Prueba de Equilibrio"
                    datos_validos1 = [
                            ("Área Izquierda", resultado1[9]),
                            ("Veces Izquierda", resultado1[10]),
                            ("Área Derecha", resultado1[11]),
                            ("Veces Derecha", resultado1[12])
                        ]
                    datos_validos2 = [
                            ("Área Izquierda", resultado2[9]),
                            ("Veces Izquierda", resultado2[10]),
                            ("Área Derecha", resultado2[11]),
                            ("Veces Derecha", resultado2[12])
                        ]
                    item_count+=2
                    self.generar_graficas_comparativas_equilibrio(resultado1, resultado2)
                    temp_plot_path_area = "grafica_comparativa_area_equilibrio.png"
                    temp_plot_path_veces = "grafica_comparativa_veces_equilibrio.png"
                     # Dibujar el título y los datos válidos en el PDF
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(margin, y_position - 30, titulo)
                  
                    # Insertar las gráficas en el PDF
                    c.drawImage(temp_plot_path_area, margin, y_position - 280, width  - 2 * margin, 200)
                    c.drawImage(temp_plot_path_veces,  margin, y_position - 480, width - 2 * margin, 200)
                    os.remove(temp_plot_path_area)  # Eliminar la imagen temporal
                    os.remove(temp_plot_path_veces)  # Eliminar la imagen temporal
                   # y_position -= 250  # Ajustar la posición vertical para el siguiente conjunto de gráficas
                    for dato1, dato2 in zip(datos_validos1, datos_validos2):
                        c.setFont("Helvetica", 12)
                        c.drawString(margin + 10, y_position - 500, f"{dato1[0]}: {dato1[1]} - {dato2[1]}")
                        y_position -= 30
                    # Calcular el progreso
                    progreso_promedio_eq= self.calcular_progreso_inicial_equilibrio(resultado1, resultado2)
                    
                    # Dibujar la barra de progreso para el área
                    meta=70
                    self.dibujar_barra_progreso_eq(c, progreso_promedio_eq, meta, margin, y_position - 590, width-2*margin, 20)
                    c.setFont("Helvetica", 12)
                    c.drawString(margin, y_position - 550, f"Progreso de Prueba de Equilibrio")
                elif id_serie_prueba1 == 4:  # BlazePods
                    self.dibujar_logotipo(c, logo_path, width, height, margin)
                    titulo = "Resultados Blazepods"
                    datos_validos1 = [
                        ("Hits", resultado1[13]),
                        ("Reacción", resultado1[14])
                    ]
                    datos_validos2 = [
                        ("Hits", resultado2[13]),
                        ("Reacción", resultado2[14])
                    ]
                    item_count += 2
                    
                    # Generar las gráficas comparativas de Blazepods
                    self.generar_grafica_comparativa_blazepods(resultado1, resultado2)
                    
                    # Obtener las rutas de las imágenes temporales generadas
                    temp_plot_path_blazepods_hits = "grafica_comparativa_blazepods_hits.png"
                    temp_plot_path_blazepods_reaccion = "grafica_comparativa_blazepods_reaccion.png"
                    
                    # Dibujar el título y los datos válidos en el PDF
                    c.setFont("Helvetica-Bold", 14)
                    c.drawString(margin, y_position - 50, titulo)
                    
                    # Insertar la gráfica de Hits en el PDF
                    c.drawImage(temp_plot_path_blazepods_hits, margin, y_position - 350, width - 2 * margin, 200)
                    os.remove(temp_plot_path_blazepods_hits)  # Eliminar la imagen temporal
                   # y_position -= 250  # Ajustar la posición vertical para el siguiente conjunto de gráficas
                    
                    # Insertar la gráfica de Reacción en el PDF
                    c.drawImage(temp_plot_path_blazepods_reaccion, margin, y_position - 580, width  - 2 * margin, 200)
                    os.remove(temp_plot_path_blazepods_reaccion)  # Eliminar la imagen temporal
                  #  y_position -= 250  # Ajustar la posición vertical para el siguiente conjunto de gráficas
                    
                    # Insertar los datos válidos en el PDF
                    for dato1, dato2 in zip(datos_validos1, datos_validos2):
                        c.setFont("Helvetica", 12)
                        c.drawString(margin + 10, y_position - 80, f"{dato1[0]}: {dato1[1]} - {dato2[1]}")
                        y_position -= 30
                    
   
                     # Calcular el progreso del atleta
                    progreso_promedio_bp = self.calcular_progreso_inicial_bp(resultado1, resultado2)
                    meta = 70  # Meta de progreso deseado
                    
                    # Dibujar la barra de progreso para Hits
                    self.dibujar_barra_progreso(c, progreso_promedio_bp, meta, margin, y_position - 590, width - 2 * margin, 20)
                    c.setFont("Helvetica", 12)
                    c.drawString(margin, y_position - 550, f"Progreso de Prueba de Reaccion")
                  #  y_position -= 70  # Ajustar la posición vertical para la siguiente sección

                if datos_validos1 and datos_validos2:
                    if item_count > 0 and item_count == items_per_page :    
                                c.showPage()
                                y_position = height - margin
                                item_count=0
        c.save()
    
    def dibujar_barra_progreso(self, c, progreso_promedio_bp, meta, x, y, width, height):
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.rect(x, y, width, height)

        # Barra de progreso
        progreso_width = width * (abs(progreso_promedio_bp) / 100)
        if progreso_promedio_bp >= 0:
            color = colors.green  # Verde para mejora
        else:
            color = colors.blue  # Azul para empeoramiento
        c.setFillColor(color)
        c.rect(x, y, progreso_width, height, fill=True)

        # Marca de meta
        meta_position = x + width * (meta / 100)
        c.setLineWidth(2)
        c.setStrokeColor(colors.red)
        c.line(meta_position, y, meta_position, y + height)

        # Texto de progreso
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(x, y - 10, f"{progreso_promedio_bp:.1f}% de {meta}%")

        # Escala de la barra
        c.setFont("Helvetica", 8)
        c.drawString(x - 10, y + height + 2, "0")
        c.drawString(x + width - 10, y + height + 2, "100")

    def dibujar_barra_progreso_eq(self, c, progreso_promedio_eq, meta, x, y, width, height):
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.rect(x, y, width, height)
        
        # Barra de progreso
        progreso_width = width * (progreso_promedio_eq / 100)
        c.setFillColor(colors.blue)
        c.rect(x, y, progreso_width, height, fill=True)

        # Marca de meta
        meta_position = x + width * (meta / 100)
        c.setLineWidth(2)
        c.setStrokeColor(colors.red)
        c.line(meta_position, y, meta_position, y + height)

        # Texto de progreso
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(x + width + 5, y + 3, f"{progreso_promedio_eq:.1f}%")

        # Escala de la barra
        c.setFont("Helvetica", 8)
        c.drawString(x - 10, y + height + 2, "0")
        c.drawString(x + width - 10, y + height + 2, "100")

    
    def dibujar_barra_progreso_salto(self, c, progreso_salto, meta, x, y, width, height):
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.rect(x, y, width, height)

        # Barra de progreso
        progreso_width = width * (abs(progreso_salto) / 100)
        if progreso_salto >= 0:
            color = colors.green  # Verde para mejora
        else:
            color = colors.blue  # Azul para empeoramiento
        c.setFillColor(color)
        c.rect(x, y, progreso_width, height, fill=True)

        # Marca de meta
        meta_position = x + width * (meta / 100)
        c.setLineWidth(2)
        c.setStrokeColor(colors.red)
        c.line(meta_position, y, meta_position, y + height)

        # Texto de progreso
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(x, y - 10, f"{progreso_salto:.1f}% de {meta}%")

        # Escala de la barra
        c.setFont("Helvetica", 8)
        c.drawString(x - 10, y + height + 2, "0")
        c.drawString(x + width - 10, y + height + 2, "100")

   



    def dibujar_barra_progreso_et(self, c, progreso_promedio_et, meta, x, y, width, height):
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.rect(x, y, width, height)

        # Calcular la posición x de la marca de la meta
        meta_x = x + (meta / 100) * width

        # Dibujar la marca de la meta
        c.setStrokeColor(colors.red)
        c.setLineWidth(1)
        c.line(meta_x, y, meta_x, y + height)

        # Barra de progreso
        progreso_width = width * (progreso_promedio_et / 100)
        c.setFillColor(colors.blue)
        c.rect(x, y, progreso_width, height, fill=True)

        # Texto de progreso
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(x + width + 5, y + 3, f"{progreso_promedio_et:.1f}%")
        # Escala de la barra
        c.setFont("Helvetica", 8)
        c.drawString(x - 10, y + height + 2, "0")
        c.drawString(x + width - 10, y + height + 2, "100")

    def dibujar_meta_progreso_individual(self, c, meta, x, y, width, height):
        c.setStrokeColor(colors.black)
        c.setLineWidth(1)
        c.rect(x, y, width, height)
        
        # Marca de meta
        meta_position = x + width * (meta / 100)
        c.setLineWidth(2)
        c.setStrokeColor(colors.red)
        c.line(meta_position, y, meta_position, y + height)
        
        # Texto de meta
        c.setFont("Helvetica", 10)
        c.setFillColor(colors.black)
        c.drawString(meta_position + 5, y + 3, f"Meta: {meta:.1f}%")
        # Escala de la barra
        c.setFont("Helvetica", 8)
        c.drawString(x - 10, y + height + 2, "0")
        c.drawString(x + width - 10, y + height + 2, "100")
            
    def crear_pdf_reporte(self, grupo_seleccionado, pdf_name,atleta_id,logo_path):
            # Obtener los detalles del atleta
            atleta_details = self.obtener_detalles_atleta(atleta_id)
            # Obtener la ruta completa del directorio de descargas
            downloads_dir = os.path.join(os.path.expanduser('~'), 'Downloads')
            # Crear un archivo temporal para almacenar las gráficas

            # Unir la ruta completa del directorio de descargas con el nombre del archivo PDF
            pdf_path = os.path.join(downloads_dir, pdf_name)
            c = canvas.Canvas(pdf_path, pagesize=letter)
            width, height = letter
            margin = 50
            items_per_page = 2
            item_count = 0
            # Dibujar el logotipo de la marca en todas las páginas
            self.dibujar_logotipo(c, logo_path, width, height,margin)
            # Dibujar los detalles del atleta en la primera página
            self.dibujar_datos_atleta(c, atleta_details, width, height)



            y_position = height - margin
            for resultado in grupo_seleccionado:
                    id_serie_prueba = resultado[16]
                    datos_validos = []
                    titulo = ""

                    if id_serie_prueba == 2:  # Eyetracker
                        titulo = "Resultados Eyetracker"
                        datos_validos = [
                            ("Distancia promedio", resultado[6]),
                            ("Desviación estándar", resultado[7]),
                            ("Distancia máxima", resultado[8])
                        ]
                        item_count += 2
                        self.generar_grafica_eyetracker(resultado)
                        temp_plot_path = "grafica_eyetracker.png"
                         # Insertar la gráfica en el PDF
                        c.drawImage(temp_plot_path, margin, y_position - 420, width - 2 * margin, 200)
                        os.remove(temp_plot_path)  # Eliminar la imagen temporal
                         # Dibujar el título y los datos válidos en el PDF
                        c.setFont("Helvetica-Bold", 14)
                        c.drawString(margin, y_position-110, titulo)
                        y_position -= 20

                        for dato in datos_validos:
                            c.setFont("Helvetica", 12)
                            c.drawString(margin + 10, y_position-120, f"{dato[0]}: {dato[1]}")
                            y_position -= 30
                        # Dibujar la barra de progreso indicativa
                        meta_progreso = 70  # Meta de progreso deseado
                        self.dibujar_meta_progreso_individual(c, meta_progreso, margin, y_position - 460, width - 2 * margin, 20)
                        c.setFont("Helvetica", 12)
                        c.drawString(margin, y_position - 450, "Meta de progreso deseada")
                       
                        
                    elif id_serie_prueba == 4:  # Blazepods
                        titulo = "Resultados Blazepods"
                        datos_validos = [
                            ("Hits", resultado[13]),
                            ("Reacción", resultado[14])
                        ]
                        item_count += 2
                        self.generar_grafica_blazepods(resultado)
                        temp_plot_path = "grafica_blazepods.png"  # Ruta temporal de la gráfica
                        # Insertar la gráfica en el PDF
                        c.drawImage(temp_plot_path, margin, y_position - 265, width - 2 * margin, 200)
                        os.remove(temp_plot_path)  # Eliminar la imagen temporal
                            # Dibujar el título y los datos válidos en el PDF
                        c.setFont("Helvetica-Bold", 14)
                        c.drawString(margin, y_position-50, titulo)
                        #y_position -= 300

                        for dato in datos_validos:
                            c.setFont("Helvetica", 12)
                            c.drawString(margin + 10, y_position-300, f"{dato[0]}: {dato[1]}")
                            y_position -= 30
                        # Dibujar la barra de progreso indicativa
                        meta_progreso = 70  # Meta de progreso deseada
                        self.dibujar_meta_progreso_individual(c, meta_progreso, margin, y_position - 350, width - 2 * margin, 20)
                        c.setFont("Helvetica", 12)
                        c.drawString(margin, y_position - 3650, "Meta de progreso deseada")

                    elif id_serie_prueba == 1:  # Salto
                         # Dibujar el logotipo de la marca en todas las páginas
                        self.dibujar_logotipo(c, logo_path, width, height,margin)
                        titulo = "Resultados Salto"
                        datos_validos = [
                            ("Altura promedio", resultado[4]),
                            ("Impulso promedio", resultado[5])
                        ]
                        # Generar y guardar las gráficas de Salto
                        item_count += 2
                        self.generar_graficas_salto(resultado)
                        # Insertar la gráfica de altura promedio en el PDF
                        c.drawImage("grafica_altura_salto.png", margin, y_position - 300, width - 2 * margin, 200)
                        os.remove("grafica_altura_salto.png")  # Eliminar la imagen temporal
                        # Insertar la gráfica de impulso promedio en el PDF
                        c.drawImage("grafica_impulso_salto.png", margin, y_position - 500, width - 2 * margin, 200)
                        os.remove("grafica_impulso_salto.png")  # Eliminar la imagen temporal
                            # Dibujar el título y los datos válidos en el PDF
                        c.setFont("Helvetica-Bold", 14)
                        c.drawString(margin, y_position, titulo)
                        y_position -= 20

                        for dato in datos_validos:
                            c.setFont("Helvetica", 12)
                            c.drawString(margin + 10, y_position, f"{dato[0]}: {dato[1]}")
                            y_position -= 30
                     # Dibujar la barra de progreso indicativa
                        meta_progreso = 70  # Meta de progreso deseada
                        self.dibujar_meta_progreso_individual(c, meta_progreso, margin, y_position - 550, width - 2 * margin, 20)
                        c.setFont("Helvetica", 12)
                        c.drawString(margin, y_position - 565, "Meta de progreso deseada")

                         
                    elif id_serie_prueba == 3:  # Equilibrio
                         # Dibujar el logotipo de la marca en todas las páginas
                        self.dibujar_logotipo(c, logo_path, width, height,margin)
                        titulo = "Resultados Equilibrio"
                        datos_validos = [
                            ("Área Izquierda", resultado[9]),
                            ("Veces Izquierda", resultado[10]),
                            ("Área Derecha", resultado[11]),
                            ("Veces Derecha", resultado[12])
                        ]
                         # Generar y guardar las gráficas de Equilibrio
                        self.generar_graficas_equilibrio(resultado)
                        # Insertar la gráfica de área vs área en el PDF
                        c.drawImage("grafica_area_equilibrio.png", margin, y_position - 350, width - 2 * margin, 200)
                        os.remove("grafica_area_equilibrio.png")  # Eliminar la imagen temporal
                        # Insertar la gráfica de veces vs veces en el PDF
                        c.drawImage("grafica_veces_equilibrio.png", margin, y_position - 600, width - 2 * margin, 200)
                        os.remove("grafica_veces_equilibrio.png")  # Eliminar la imagen temporal
                            # Dibujar el título y los datos válidos en el PDF
                        c.setFont("Helvetica-Bold", 14)
                        c.drawString(margin, y_position, titulo)
                       # y_position -= 220

                        for dato in datos_validos:
                            c.setFont("Helvetica", 12)
                            c.drawString(margin + 10, y_position-50, f"{dato[0]}: {dato[1]}")
                            y_position -= 30
                         # Dibujar la barra de progreso indicativa
                        meta_progreso = 70  # Meta de progreso deseada
                        self.dibujar_meta_progreso_individual(c, meta_progreso, margin, y_position - 570, width - 2 * margin, 20)
                        c.setFont("Helvetica", 12)
                        c.drawString(margin, y_position - 560, "Meta de progreso deseada")

                         
                    if datos_validos:
                        if item_count > 0 and item_count == items_per_page :
                             c.showPage()
                             y_position = height - margin
                             item_count=0

                        #y_position -= 150  # Espacio entre secciones
                           
                          # Ajustar la posición para la siguiente sección
                        #item_count += 1
            c.save()  # Guardar el PDF
    def obtener_detalles_atleta(self, id_atleta):
        # Realizar la consulta para obtener los detalles del atleta
        c.execute("""
            SELECT a.nombre, a.edad, a.peso, a.altura, a.deporte
            FROM resultados_pruebas rp
            JOIN atletas a ON rp.id_atleta = a.id
            WHERE rp.id_atleta = ?
            LIMIT 1
        """, (id_atleta,))
        atleta_details = c.fetchone()

        # Devolver los detalles del atleta como un diccionario
        return {
            "Nombre": atleta_details[0],
            "Edad": atleta_details[1],
            "Peso": atleta_details[2],
            "Altura": atleta_details[3],
            "Deporte": atleta_details[4]
        }

    def dibujar_datos_atleta(self, c, atleta_details, width, height):
        # Lógica para dibujar los datos del atleta en la primera página del PDF
        y_position = height - 50
        for key, value in atleta_details.items():
            c.drawString(50, y_position, f"{key}: {value}")
            y_position -= 20

    def dibujar_logotipo(self, c, logo_path, width, height,margin):
        
        # Obtener las dimensiones del logotipo
        logo_width, logo_height = Image.open(logo_path).size
        
        # Definir las coordenadas para colocar el logotipo en la esquina superior derecha
        x_position = width - margin - logo_width  # margin es el margen derecho deseado
        y_position = height - margin - logo_height  # margin es el margen superior deseado
        
        # Dibujar el logotipo en las coordenadas calculadas
        c.drawImage(logo_path, x_position, y_position, logo_width, logo_height)
 
    def generar_grafica_eyetracker(self, resultado):
        # Extraer los datos relevantes del resultado para la gráfica
        distancia_promedio = resultado[6]
        desviacion_estandar = resultado[7]
        distancia_maxima = resultado[8]

        # Definir etiquetas y valores para la gráfica
        etiquetas = ['Distancia promedio', 'Desviación estándar', 'Distancia máxima']
        valores = [distancia_promedio, desviacion_estandar, distancia_maxima]

        # Crear la gráfica
        plt.figure()
        plt.bar(etiquetas, valores, color=['#4c72b0', '#dd8452', '#55a868'])
        plt.title('Resultados Eyetracker')
        plt.xlabel('Parámetros')
        plt.ylabel('Valores')
        plt.grid(True)
        plt.tight_layout()  # Ajustar el diseño de la gráfica
        plt.savefig('grafica_eyetracker.png')  # Guardar la gráfica como imagen
        plt.close()
    def generar_grafica_blazepods(self, resultado):
        # Extraer los datos relevantes del resultado para la gráfica
        hits = resultado[13]
        reaccion = resultado[14]

        # Definir etiquetas y valores para la gráfica
        etiquetas = ['Hits', 'Reacción']
        valores = [hits, reaccion]

        # Crear la gráfica
        plt.figure()
        plt.bar(etiquetas, valores, color=['#c44e52', '#8172b2'])
        plt.title('Resultados Blazepods')
        plt.xlabel('Parámetros')
        plt.ylabel('Valores')
        plt.grid(True)
        plt.tight_layout()  # Ajustar el diseño de la gráfica
        plt.savefig('grafica_blazepods.png')  # Guardar la gráfica como imagen
        plt.close()
    def generar_graficas_salto(self, resultado):
        # Extraer los datos relevantes del resultado para la gráfica
        altura_promedio = resultado[4]
        impulso_promedio = resultado[5]

        # Definir etiquetas y valores para la gráfica de altura promedio
        etiquetas_altura = ['Altura promedio']
        valores_altura = [altura_promedio]

        # Crear la gráfica de altura promedio
        plt.figure()
        plt.bar(etiquetas_altura, valores_altura, color='#4c72b0',width=0.1, linewidth=0.2)
        plt.title('Altura Promedio en Salto')
        plt.xlabel('Parámetros')
        plt.ylabel('Valores')
        plt.grid(True)
        plt.tight_layout()  # Ajustar el diseño de la gráfica
        plt.savefig('grafica_altura_salto.png')  # Guardar la gráfica como imagen
        plt.close()

        # Definir etiquetas y valores para la gráfica de impulso promedio
        etiquetas_impulso = ['Impulso promedio']
        valores_impulso = [impulso_promedio]

        # Crear la gráfica de impulso promedio
        plt.figure()
        plt.bar(etiquetas_impulso, valores_impulso, color='#dd8452',width=0.1, linewidth=0.2)
        plt.title('Impulso Promedio en Salto')
        plt.xlabel('Parámetros')
        plt.ylabel('Valores')
        plt.grid(True)
        plt.tight_layout()  # Ajustar el diseño de la gráfica
        plt.savefig('grafica_impulso_salto.png')  # Guardar la gráfica como imagen
        plt.close()
    def generar_graficas_equilibrio(self, resultado):
        # Extraer los datos relevantes del resultado para la gráfica
        area_izquierda = resultado[9]
        veces_izquierda = resultado[10]
        area_derecha = resultado[11]
        veces_derecha = resultado[12]

        # Definir etiquetas y valores para la gráfica de área izquierda vs área derecha
        etiquetas_area = ['Área Izquierda', 'Área Derecha']
        valores_area = [area_izquierda, area_derecha]

        # Crear la gráfica de área izquierda vs área derecha
        plt.figure()
        plt.bar(etiquetas_area, valores_area, color=['#55a868', '#c44e52'])
        plt.title('Área Izquierda vs Área Derecha en Equilibrio')
        plt.xlabel('Parámetros')
        plt.ylabel('Valores')
        plt.grid(True)
        plt.tight_layout()  # Ajustar el diseño de la gráfica
        plt.savefig('grafica_area_equilibrio.png')  # Guardar la gráfica como imagen
        plt.close()

        # Definir etiquetas y valores para la gráfica de veces izquierda vs veces derecha
        etiquetas_veces = ['Veces Izquierda', 'Veces Derecha']
        valores_veces = [veces_izquierda, veces_derecha]

        # Crear la gráfica de veces izquierda vs veces derecha
        plt.figure()
        plt.bar(etiquetas_veces, valores_veces, color=['blue', 'orange'])
        plt.title('Veces Izquierda vs Veces Derecha en Equilibrio')
        plt.xlabel('Parámetros')
        plt.ylabel('Valores')
        plt.grid(True)
        plt.tight_layout()  # Ajustar el diseño de la gráfica
        plt.savefig('grafica_veces_equilibrio.png')  # Guardar la gráfica como imagen
        plt.close()
    def generar_grafica_comparativa_eyetracker(self, resultado1, resultado2):
        # Extraer los datos relevantes del primer resultado para la gráfica
        distancia_promedio1 = resultado1[6]
        desviacion_estandar1 = resultado1[7]
        distancia_maxima1 = resultado1[8]

        # Extraer los datos relevantes del segundo resultado para la gráfica
        distancia_promedio2 = resultado2[6]
        desviacion_estandar2 = resultado2[7]
        distancia_maxima2 = resultado2[8]

        # Definir etiquetas y valores para la gráfica
        etiquetas = ['Distancia promedio', 'Desviación estándar', 'Distancia máxima']
        valores1 = [distancia_promedio1, desviacion_estandar1, distancia_maxima1]
        valores2 = [distancia_promedio2, desviacion_estandar2, distancia_maxima2]

        # Definir la posición de cada barra en la gráfica
        x = np.arange(len(etiquetas))
        width = 0.35  # Ancho de las barras

        # Crear la gráfica comparativa
        fig, ax = plt.subplots()
        ax.bar(x - width/2, valores1, width, label='Grupo 1')
        ax.bar(x + width/2, valores2, width, label='Grupo 2')

        # Agregar etiquetas, título y leyenda
        ax.set_xlabel('Parámetros')
        ax.set_ylabel('Valores')
        ax.set_title('Resultados Eyetracker - Comparativa')
        ax.set_xticks(x)
        ax.set_xticklabels(etiquetas)
        ax.legend()

        # Guardar la gráfica como imagen temporal
        plt.tight_layout()
        plt.savefig('grafica_comparativa_eyetracker.png')
        plt.close()
    def generar_grafica_comparativa_blazepods(self, resultado1, resultado2):
        # Extraer los datos relevantes del primer resultado para la gráfica
        hits1 = resultado1[13]
        reaccion1 = resultado1[14]

        # Extraer los datos relevantes del segundo resultado para la gráfica
        hits2 = resultado2[13]
        reaccion2 = resultado2[14]

        # Definir etiquetas y valores para la gráfica de Hits
        etiquetas_hits = ['Hits']
        valores_hits1 = [hits1]
        valores_hits2 = [hits2]

        # Definir etiquetas y valores para la gráfica de Reacción
        etiquetas_reaccion = ['Reacción']
        valores_reaccion1 = [reaccion1]
        valores_reaccion2 = [reaccion2]

        # Definir la posición de cada barra en la gráfica
        x_hits = np.arange(len(etiquetas_hits))
        x_reaccion = np.arange(len(etiquetas_reaccion))
        width = 0.3  # Ancho de las barras

        # Crear la gráfica comparativa de Hits
        fig, ax = plt.subplots()
        ax.bar(x_hits - width/2, valores_hits1, width, label='Grupo 1')
        ax.bar(x_hits + width/2, valores_hits2, width, label='Grupo 2')
        ax.set_xlabel('Parámetros')
        ax.set_ylabel('Valores')
        ax.set_title('Resultados Blazepods - Hits')
        ax.set_xticks(x_hits)
        ax.set_xticklabels(etiquetas_hits)
        ax.legend()

        # Guardar la gráfica como imagen temporal
        plt.tight_layout()
        plt.savefig('grafica_comparativa_blazepods_hits.png')
        plt.close()

        # Crear la gráfica comparativa de Reacción
        fig, ax = plt.subplots()
        ax.bar(x_reaccion - width/2, valores_reaccion1, width, label='Grupo 1')
        ax.bar(x_reaccion + width/2, valores_reaccion2, width, label='Grupo 2')
        ax.set_xlabel('Parámetros')
        ax.set_ylabel('Valores')
        ax.set_title('Resultados Blazepods - Reacción')
        ax.set_xticks(x_reaccion)
        ax.set_xticklabels(etiquetas_reaccion)
        ax.legend()

        # Guardar la gráfica como imagen temporal
        plt.tight_layout()
        plt.savefig('grafica_comparativa_blazepods_reaccion.png')
        plt.close()



    def generar_graficas_comparativas_salto(self, resultado1, resultado2):
        # Extraer los datos relevantes del primer resultado para las gráficas
        altura_promedio1 = resultado1[4]
        impulso_promedio1 = resultado1[5]

        # Extraer los datos relevantes del segundo resultado para las gráficas
        altura_promedio2 = resultado2[4]
        impulso_promedio2 = resultado2[5]

        # Definir etiquetas y valores para las gráficas de altura promedio
        etiquetas_altura = ['Altura promedio']
        valores_altura1 = [altura_promedio1]
        valores_altura2 = [altura_promedio2]

        # Definir la posición de cada barra en las gráficas
        x = np.arange(len(etiquetas_altura))
        width = 0.35  # Ancho de las barras

        # Crear la gráfica comparativa de altura promedio
        fig, ax = plt.subplots()
        ax.bar(x - width/2, valores_altura1, width, label='Grupo 1')
        ax.bar(x + width/2, valores_altura2, width, label='Grupo 2')

        # Agregar etiquetas, título y leyenda
        ax.set_xlabel('Parámetros')
        ax.set_ylabel('Valores')
        ax.set_title('Altura Promedio en Salto - Comparativa')
        ax.set_xticks(x)
        ax.set_xticklabels(etiquetas_altura)
        ax.legend()

        # Guardar la gráfica como imagen temporal
        plt.tight_layout()
        plt.savefig('grafica_comparativa_altura_salto.png')
        plt.close()

        # Definir etiquetas y valores para las gráficas de impulso promedio
        etiquetas_impulso = ['Impulso promedio']
        valores_impulso1 = [impulso_promedio1]
        valores_impulso2 = [impulso_promedio2]

        # Crear la gráfica comparativa de impulso promedio
        fig, ax = plt.subplots()
        ax.bar(x - width/2, valores_impulso1, width, label='Grupo 1')
        ax.bar(x + width/2, valores_impulso2, width, label='Grupo 2')

        # Agregar etiquetas, título y leyenda
        ax.set_xlabel('Parámetros')
        ax.set_ylabel('Valores')
        ax.set_title('Impulso Promedio en Salto - Comparativa')
        ax.set_xticks(x)
        ax.set_xticklabels(etiquetas_impulso)
        ax.legend()

        # Guardar la gráfica como imagen temporal
        plt.tight_layout()
        plt.savefig('grafica_comparativa_impulso_salto.png')
        plt.close()

    def generar_graficas_comparativas_equilibrio(self, resultado1, resultado2):
        # Extraer los datos relevantes del primer resultado para las gráficas
        area_izquierda1 = resultado1[9]
        veces_izquierda1 = resultado1[10]
        area_derecha1 = resultado1[11]
        veces_derecha1 = resultado1[12]

        # Extraer los datos relevantes del segundo resultado para las gráficas
        area_izquierda2 = resultado2[9]
        veces_izquierda2 = resultado2[10]
        area_derecha2 = resultado2[11]
        veces_derecha2 = resultado2[12]

        # Definir etiquetas y valores para las gráficas de área izquierda vs área derecha
        etiquetas_area = ['Área Izquierda', 'Área Derecha']
        valores_area1 = [area_izquierda1, area_derecha1]
        valores_area2 = [area_izquierda2, area_derecha2]

        # Definir la posición de cada barra en las gráficas
        x = np.arange(len(etiquetas_area))
        width = 0.35  # Ancho de las barras

        # Crear la gráfica comparativa de área izquierda vs área derecha
        fig, ax = plt.subplots()
        ax.bar(x - width/2, valores_area1, width, label='Grupo 1')
        ax.bar(x + width/2, valores_area2, width, label='Grupo 2')

        # Agregar etiquetas, título y leyenda
        ax.set_xlabel('Parámetros')
        ax.set_ylabel('Valores')
        ax.set_title('Área Izquierda vs Área Derecha en Equilibrio - Comparativa')
        ax.set_xticks(x)
        ax.set_xticklabels(etiquetas_area)
        ax.legend()

        # Guardar la gráfica como imagen temporal
        plt.tight_layout()
        plt.savefig('grafica_comparativa_area_equilibrio.png')
        plt.close()

        # Definir etiquetas y valores para las gráficas de veces izquierda vs veces derecha
        etiquetas_veces = ['Veces Izquierda', 'Veces Derecha']
        valores_veces1 = [veces_izquierda1, veces_derecha1]
        valores_veces2 = [veces_izquierda2, veces_derecha2]

        # Crear la gráfica comparativa de veces izquierda vs veces derecha
        fig, ax = plt.subplots()
        ax.bar(x - width/2, valores_veces1, width, label='Grupo 1')
        ax.bar(x + width/2, valores_veces2, width, label='Grupo 2')

        # Agregar etiquetas, título y leyenda
        ax.set_xlabel('Parámetros')
        ax.set_ylabel('Valores')
        ax.set_title('Veces Izquierda vs Veces Derecha en Equilibrio - Comparativa')
        ax.set_xticks(x)
        ax.set_xticklabels(etiquetas_veces)
        ax.legend()

        # Guardar la gráfica como imagen temporal
        plt.tight_layout()
        plt.savefig('grafica_comparativa_veces_equilibrio.png')
        plt.close()
class SeleccionarGruposPruebasDialog:
    def __init__(self, parent, grupos_pruebas):
        self.top = tk.Toplevel(parent)
        self.top.title("Seleccionar Grupos de Pruebas")

        self.grupo_seleccionado1 = None
        self.grupo_seleccionado2 = None

        tk.Label(self.top, text="Seleccione el primer grupo de pruebas:").pack(pady=5)
        self.lista_grupos1 = tk.Listbox(self.top, selectmode=tk.SINGLE, exportselection=0)
        self.lista_grupos1.pack(pady=5)

        tk.Label(self.top, text="Seleccione el segundo grupo de pruebas:").pack(pady=5)
        self.lista_grupos2 = tk.Listbox(self.top, selectmode=tk.SINGLE, exportselection=0)
        self.lista_grupos2.pack(pady=5)

        for i, grupo in enumerate(grupos_pruebas):
            self.lista_grupos1.insert(tk.END, f"Grupo {i+1}")
            self.lista_grupos2.insert(tk.END, f"Grupo {i+1}")

        tk.Button(self.top, text="Aceptar", command=lambda: self.aceptar(grupos_pruebas)).pack(pady=10)

    def aceptar(self,grupos_pruebas):
        seleccion1 = self.lista_grupos1.curselection()
        seleccion2 = self.lista_grupos2.curselection()

     #   print("Seleccion1:", seleccion1)  # Línea de depuración
       # print("Seleccion2:", seleccion2)  # Línea de depuración

        if seleccion1 and seleccion2:
            grupo_seleccionado1 = grupos_pruebas[seleccion1[0]]
            grupo_seleccionado2 = grupos_pruebas[seleccion2[0]]

           # print("Grupo seleccionado 1:", grupo_seleccionado1)  # Línea de depuración
          #  print("Grupo seleccionado 2:", grupo_seleccionado2)  # Línea de depuración

            if grupo_seleccionado1 != grupo_seleccionado2:
                self.resultado = (grupo_seleccionado1, grupo_seleccionado2)
                self.top.destroy()
            else:
                messagebox.showerror("Error", "Debe seleccionar dos grupos de pruebas diferentes.")
        else:
            messagebox.showerror("Error", "Debe seleccionar dos grupos de pruebas.")




def registrar_atleta():
    dialogo = RegistroAtletaDialog(root)
    if dialogo.result:
        root.withdraw()
        DetallesAtletaDialog(root, dialogo.result)

def cargar_atleta():
    c.execute("SELECT * FROM atletas")
    atletas = c.fetchall()

    if not atletas:
        messagebox.showinfo("Cargar Atleta", "No hay atletas registrados.")
        return

    # Crear una nueva ventana
    top = Toplevel(root)
    top.title("Cargar Atleta")

    # Crear un Listbox para mostrar los nombres de los atletas
    listbox = Listbox(top)
    listbox.pack()

    # Agregar los nombres de los atletas al Listbox
    for atleta in atletas:
        listbox.insert(tk.END, atleta[1])

    # Función para manejar la selección del atleta
    def on_select(event):
        # Obtener el nombre del atleta seleccionado
        seleccion = listbox.get(listbox.curselection())
        for atleta in atletas:
            if atleta[1] == seleccion:
                atleta_dict = {"id":atleta[0],"nombre": atleta[1], "edad": atleta[2], "peso": atleta[3], "altura": atleta[4], "deporte": atleta[5]}
                break
        top.destroy()
        root.withdraw()
        DetallesAtletaDialog(root, atleta_dict)

    # Vincular el evento de selección del Listbox a la función on_select
    listbox.bind('<<ListboxSelect>>', on_select)
def generar_reportes():
    dialogo = GeneradorReportes()
# Crear ventana principal
root = tk.Tk()
root.title("Registro de Atletas")
root.geometry("300x200")  # Tamaño personalizado de la ventana

    # Etiqueta de título
label_titulo = tk.Label(root, text="Bienvenido al Registro de Atletas", font=("Helvetica", 14))
label_titulo.pack(pady=20)

    # Botón para registrar atleta
btn_registrar = tk.Button(root, text="Registrar Atleta", command=registrar_atleta, bg="#007acc", fg="white")
btn_registrar.pack(pady=10)

    # Botón para cargar atleta
btn_cargar = tk.Button(root, text="Cargar Atleta", command=cargar_atleta, bg="#007acc", fg="white")
btn_cargar.pack(pady=10)
# Botón para generar reportes
btn_reportes = tk.Button(root, text="Generar Reportes", command=generar_reportes, bg="#007acc", fg="white")
btn_reportes.pack(pady=10)
    # Ejecutar la interfaz
root.mainloop()

    # Cerrar la conexión a la base de datos
conn.close()
