"""
Utilidades para generar reportes gráficos
"""
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter as tk
from datetime import datetime, timedelta

class ReportGenerator:
    @staticmethod
    def create_cash_flow_chart(parent, cash_data, title="Flujo de Caja"):
        """Crear gráfico de flujo de caja"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        dates = [item['date'] for item in cash_data]
        income = [item['income'] for item in cash_data]
        expense = [item['expense'] for item in cash_data]
        balance = [item['balance'] for item in cash_data]
        
        width = 0.35
        x = range(len(dates))
        
        ax.bar(x, income, width, label='Ingresos', color='green', alpha=0.7)
        ax.bar(x, expense, width, label='Egresos', color='red', alpha=0.7, bottom=income)
        ax.plot(x, balance, 'b-', label='Balance', linewidth=2, marker='o')
        
        ax.set_xlabel('Fecha')
        ax.set_ylabel('Monto ($)')
        ax.set_title(title)
        ax.set_xticks(x)
        ax.set_xticklabels(dates, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        fig.tight_layout()
        
        # Embedder en TK
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        return canvas
    
    @staticmethod
    def create_loans_status_chart(parent, loans_data):
        """Crear gráfico de estado de préstamos"""
        fig, ax = plt.subplots(figsize=(8, 6))
        
        status_counts = {}
        for loan in loans_data:
            status = loan['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        labels = []
        counts = []
        colors = []
        
        status_translation = {
            'active': 'Activos',
            'paid': 'Pagados',
            'overdue': 'Vencidos'
        }
        
        color_map = {
            'active': 'lightblue',
            'paid': 'lightgreen',
            'overdue': 'lightcoral'
        }
        
        for status, count in status_counts.items():
            labels.append(status_translation.get(status, status))
            counts.append(count)
            colors.append(color_map.get(status, 'gray'))
        
        ax.pie(counts, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        ax.set_title('Estado de Préstamos')
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        return canvas
    
    @staticmethod
    def create_inventory_stock_chart(parent, stock_data):
        """Crear gráfico de stock de inventario"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Agrupar por tipo y calidad
        categories = []
        stocks = []
        colors = []
        
        color_map = {
            'parda': 'sienna',
            'amarilla': 'gold',
            'colorada': 'indianred'
        }
        
        for item in stock_data:
            label = f"{item['potato_type']} {item['quality']}"
            categories.append(label)
            stocks.append(item['current_stock'])
            colors.append(color_map.get(item['potato_type'], 'gray'))
        
        bars = ax.bar(categories, stocks, color=colors, alpha=0.7)
        ax.set_xlabel('Categoría')
        ax.set_ylabel('Stock (costales)')
        ax.set_title('Stock Actual de Inventario')
        ax.tick_params(axis='x', rotation=45)
        ax.grid(True, alpha=0.3)
        
        # Agregar valores en las barras
        for bar, stock in zip(bars, stocks):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 0.5,
                   f'{stock}', ha='center', va='bottom')
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        return canvas
    
    @staticmethod
    def create_monthly_comparison_chart(parent, monthly_data, title="Comparación Mensual"):
        """Crear gráfico de comparación mensual"""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        months = [item['month'] for item in monthly_data]
        values = [item['value'] for item in monthly_data]
        
        ax.plot(months, values, 'o-', linewidth=2, markersize=8)
        ax.set_xlabel('Mes')
        ax.set_ylabel('Valor')
        ax.set_title(title)
        ax.grid(True, alpha=0.3)
        ax.tick_params(axis='x', rotation=45)
        
        # Agregar valores en los puntos
        for i, v in enumerate(values):
            ax.text(i, v + max(values) * 0.01, f'{v:.2f}', ha='center', va='bottom')
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        return canvas