import sqlite3
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

BANCO = Path(__file__).with_name("pedidos_otica.db")
TIPOS_SERVICO = [
    "Óculos completo",
    "Troca de lente",
    "Limpeza de óculos",
    "Conserto de óculos",
    "Solda de óculos",
]
STATUS = ["Recebido", "Em execução", "Pronto", "Entregue", "Cancelado"]


class BancoPedidos:
    def __init__(self, caminho=BANCO):
        self.caminho = caminho
        self.criar_tabela()

    def conectar(self):
        conexao = sqlite3.connect(self.caminho)
        conexao.row_factory = sqlite3.Row
        return conexao

    def criar_tabela(self):
        with self.conectar() as conexao:
            conexao.execute(
                """
                CREATE TABLE IF NOT EXISTS pedidos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cliente TEXT NOT NULL,
                    telefone TEXT NOT NULL,
                    servico TEXT NOT NULL,
                    data_pedido TEXT NOT NULL,
                    valor REAL NOT NULL,
                    prazo_entrega TEXT NOT NULL,
                    status TEXT NOT NULL,
                    observacoes TEXT
                )
                """
            )

    def inserir(self, dados):
        with self.conectar() as conexao:
            conexao.execute(
                """
                INSERT INTO pedidos
                (cliente, telefone, servico, data_pedido, valor,
                 prazo_entrega, status, observacoes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                dados,
            )

    def atualizar(self, pedido_id, dados):
        with self.conectar() as conexao:
            conexao.execute(
                """
                UPDATE pedidos
                SET cliente = ?, telefone = ?, servico = ?, data_pedido = ?,
                    valor = ?, prazo_entrega = ?, status = ?, observacoes = ?
                WHERE id = ?
                """,
                (*dados, pedido_id),
            )

    def excluir(self, pedido_id):
        with self.conectar() as conexao:
            conexao.execute("DELETE FROM pedidos WHERE id = ?", (pedido_id,))

    def buscar(self, texto="", filtro_status="Todos", filtro_servico="Todos"):
        consulta = "SELECT * FROM pedidos WHERE 1 = 1"
        parametros = []

        if texto:
            consulta += " AND (LOWER(cliente) LIKE LOWER(?) OR telefone LIKE ? OR CAST(id AS TEXT) = ?)"
            termo = f"%{texto}%"
            parametros.extend([termo, termo, texto])
        if filtro_status != "Todos":
            consulta += " AND status = ?"
            parametros.append(filtro_status)
        if filtro_servico != "Todos":
            consulta += " AND servico = ?"
            parametros.append(filtro_servico)

        consulta += " ORDER BY id DESC"
        with self.conectar() as conexao:
            return conexao.execute(consulta, parametros).fetchall()

    def resumo(self):
        with self.conectar() as conexao:
            total = conexao.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
            valor = conexao.execute("SELECT COALESCE(SUM(valor), 0) FROM pedidos").fetchone()[0]
            pendentes = conexao.execute(
                "SELECT COUNT(*) FROM pedidos WHERE status NOT IN ('Entregue', 'Cancelado')"
            ).fetchone()[0]
            return total, valor, pendentes


class Aplicativo:
    def __init__(self, janela):
        self.janela = janela
        self.janela.title("Sistema de Controle de Pedidos - Ótica")
        self.janela.geometry("1180x720")
        self.janela.minsize(980, 600)
        self.banco = BancoPedidos()
        self.pedido_selecionado = None

        self.configurar_estilo()
        self.criar_formulario()
        self.criar_filtros()
        self.criar_tabela()
        self.criar_botoes()
        self.atualizar_tela()

    def configurar_estilo(self):
        estilo = ttk.Style()
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure("Atrasado.Treeview", background="#ffe0e0")
        estilo.configure("Resumo.TLabel", font=("Arial", 10, "bold"))

    def criar_formulario(self):
        quadro = ttk.LabelFrame(self.janela, text="Dados do pedido", padding=10)
        quadro.pack(fill="x", padx=10, pady=10)

        ttk.Label(quadro, text="Cliente *").grid(row=0, column=0, sticky="w", padx=5, pady=4)
        self.cliente = ttk.Entry(quadro, width=28)
        self.cliente.grid(row=0, column=1, sticky="ew", padx=5, pady=4)

        ttk.Label(quadro, text="Telefone *").grid(row=0, column=2, sticky="w", padx=5, pady=4)
        self.telefone = ttk.Entry(quadro, width=18)
        self.telefone.grid(row=0, column=3, sticky="ew", padx=5, pady=4)

        ttk.Label(quadro, text="Serviço *").grid(row=0, column=4, sticky="w", padx=5, pady=4)
        self.servico = ttk.Combobox(quadro, values=TIPOS_SERVICO, state="readonly", width=22)
        self.servico.grid(row=0, column=5, sticky="ew", padx=5, pady=4)
        self.servico.current(0)

        ttk.Label(quadro, text="Data do pedido *").grid(row=1, column=0, sticky="w", padx=5, pady=4)
        self.data_pedido = ttk.Entry(quadro, width=15)
        self.data_pedido.grid(row=1, column=1, sticky="w", padx=5, pady=4)
        self.data_pedido.insert(0, self.data_hoje())

        ttk.Label(quadro, text="Valor (R$) *").grid(row=1, column=2, sticky="w", padx=5, pady=4)
        self.valor = ttk.Entry(quadro, width=15)
        self.valor.grid(row=1, column=3, sticky="w", padx=5, pady=4)

        ttk.Label(quadro, text="Prazo de entrega *").grid(row=1, column=4, sticky="w", padx=5, pady=4)
        self.prazo = ttk.Entry(quadro, width=15)
        self.prazo.grid(row=1, column=5, sticky="w", padx=5, pady=4)

        ttk.Label(quadro, text="Status").grid(row=2, column=0, sticky="w", padx=5, pady=4)
        self.status = ttk.Combobox(quadro, values=STATUS, state="readonly", width=25)
        self.status.grid(row=2, column=1, sticky="ew", padx=5, pady=4)
        self.status.set("Recebido")

        ttk.Label(quadro, text="Observações").grid(row=2, column=2, sticky="w", padx=5, pady=4)
        self.observacoes = ttk.Entry(quadro, width=45)
        self.observacoes.grid(row=2, column=3, columnspan=3, sticky="ew", padx=5, pady=4)

        for coluna in range(6):
            quadro.columnconfigure(coluna, weight=1)

    def criar_filtros(self):
        quadro = ttk.LabelFrame(self.janela, text="Busca e filtros", padding=8)
        quadro.pack(fill="x", padx=10, pady=(0, 10))

        ttk.Label(quadro, text="Buscar:").pack(side="left", padx=(0, 5))
        self.busca = ttk.Entry(quadro, width=28)
        self.busca.pack(side="left", padx=5)
        self.busca.bind("<KeyRelease>", lambda evento: self.atualizar_tela())

        ttk.Label(quadro, text="Status:").pack(side="left", padx=(15, 5))
        self.filtro_status = ttk.Combobox(quadro, values=["Todos"] + STATUS, state="readonly", width=16)
        self.filtro_status.pack(side="left", padx=5)
        self.filtro_status.set("Todos")
        self.filtro_status.bind("<<ComboboxSelected>>", lambda evento: self.atualizar_tela())

        ttk.Label(quadro, text="Serviço:").pack(side="left", padx=(15, 5))
        self.filtro_servico = ttk.Combobox(
            quadro, values=["Todos"] + TIPOS_SERVICO, state="readonly", width=20
        )
        self.filtro_servico.pack(side="left", padx=5)
        self.filtro_servico.set("Todos")
        self.filtro_servico.bind("<<ComboboxSelected>>", lambda evento: self.atualizar_tela())

        ttk.Button(quadro, text="Limpar filtros", command=self.limpar_filtros).pack(side="left", padx=15)

    def criar_tabela(self):
        quadro = ttk.LabelFrame(self.janela, text="Pedidos cadastrados", padding=8)
        quadro.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        colunas = ("id", "cliente", "telefone", "servico", "data", "valor", "prazo", "status", "obs")
        self.tabela = ttk.Treeview(quadro, columns=colunas, show="headings", selectmode="browse")
        cabecalhos = {
            "id": "Nº", "cliente": "Cliente", "telefone": "Telefone", "servico": "Serviço",
            "data": "Data", "valor": "Valor", "prazo": "Prazo", "status": "Status", "obs": "Observações"
        }
        larguras = {"id": 45, "cliente": 140, "telefone": 110, "servico": 135, "data": 85,
                    "valor": 80, "prazo": 85, "status": 105, "obs": 190}
        for coluna in colunas:
            self.tabela.heading(coluna, text=cabecalhos[coluna])
            self.tabela.column(coluna, width=larguras[coluna], anchor="center")
        self.tabela.tag_configure("atrasado", background="#ffd6d6")
        self.tabela.bind("<<TreeviewSelect>>", self.selecionar_pedido)

        barra = ttk.Scrollbar(quadro, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=barra.set)
        self.tabela.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")

    def criar_botoes(self):
        quadro = ttk.Frame(self.janela)
        quadro.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Button(quadro, text="Novo / Limpar", command=self.limpar_formulario).pack(side="left", padx=4)
        ttk.Button(quadro, text="Cadastrar", command=self.cadastrar).pack(side="left", padx=4)
        ttk.Button(quadro, text="Editar selecionado", command=self.editar).pack(side="left", padx=4)
        ttk.Button(quadro, text="Excluir selecionado", command=self.excluir).pack(side="left", padx=4)

        self.resumo_label = ttk.Label(quadro, text="", style="Resumo.TLabel")
        self.resumo_label.pack(side="right", padx=5)
        ttk.Label(self.janela, text="Linhas em vermelho indicam pedidos fora do prazo.").pack(anchor="w", padx=15, pady=(0, 8))

    @staticmethod
    def data_hoje():
        return datetime.now().strftime("%d/%m/%Y")

    @staticmethod
    def data_valida(texto):
        try:
            datetime.strptime(texto, "%d/%m/%Y")
            return True
        except ValueError:
            return False

    @staticmethod
    def moeda(texto):
        return float(texto.strip().replace("R$", "").replace(".", "").replace(",", "."))

    def dados_formulario(self):
        cliente = self.cliente.get().strip()
        telefone = self.telefone.get().strip()
        data_pedido = self.data_pedido.get().strip()
        prazo = self.prazo.get().strip()
        if not cliente or not telefone or not data_pedido or not prazo:
            raise ValueError("Preencha todos os campos obrigatórios (*).")
        if not self.data_valida(data_pedido) or not self.data_valida(prazo):
            raise ValueError("As datas devem estar no formato dd/mm/aaaa.")
        try:
            valor = self.moeda(self.valor.get())
            if valor < 0:
                raise ValueError
        except (ValueError, AttributeError):
            raise ValueError("Digite um valor válido, por exemplo: 450,00.")
        return (
            cliente, telefone, self.servico.get(), data_pedido, valor,
            prazo, self.status.get(), self.observacoes.get().strip()
        )

    def cadastrar(self):
        try:
            dados = self.dados_formulario()
            self.banco.inserir(dados)
            self.limpar_formulario()
            self.atualizar_tela()
            messagebox.showinfo("Sucesso", "Pedido cadastrado com sucesso.")
        except ValueError as erro:
            messagebox.showerror("Dados inválidos", str(erro))

    def editar(self):
        if self.pedido_selecionado is None:
            messagebox.showwarning("Atenção", "Selecione um pedido na tabela para editar.")
            return
        try:
            dados = self.dados_formulario()
            self.banco.atualizar(self.pedido_selecionado, dados)
            self.limpar_formulario()
            self.atualizar_tela()
            messagebox.showinfo("Sucesso", "Pedido atualizado com sucesso.")
        except ValueError as erro:
            messagebox.showerror("Dados inválidos", str(erro))

    def excluir(self):
        if self.pedido_selecionado is None:
            messagebox.showwarning("Atenção", "Selecione um pedido na tabela para excluir.")
            return
        confirmar = messagebox.askyesno("Confirmar exclusão", "Deseja realmente excluir este pedido?")
        if confirmar:
            self.banco.excluir(self.pedido_selecionado)
            self.limpar_formulario()
            self.atualizar_tela()
            messagebox.showinfo("Sucesso", "Pedido excluído.")

    def selecionar_pedido(self, evento=None):
        selecionado = self.tabela.selection()
        if not selecionado:
            self.pedido_selecionado = None
            return
        valores = self.tabela.item(selecionado[0], "values")
        self.pedido_selecionado = int(valores[0])
        self.preencher_formulario(self.pedido_selecionado)

    def preencher_formulario(self, pedido_id):
        registro = next((item for item in self.banco.buscar() if item["id"] == pedido_id), None)
        if registro is None:
            return
        campos = [
            (self.cliente, registro["cliente"]),
            (self.telefone, registro["telefone"]),
            (self.data_pedido, registro["data_pedido"]),
            (self.valor, f"{registro['valor']:.2f}"),
            (self.prazo, registro["prazo_entrega"]),
            (self.observacoes, registro["observacoes"] or ""),
        ]
        for campo, valor in campos:
            campo.delete(0, tk.END)
            campo.insert(0, valor)
        self.servico.set(registro["servico"])
        self.status.set(registro["status"])

    def pedido_atrasado(self, registro):
        if registro["status"] in ("Entregue", "Cancelado"):
            return False
        try:
            prazo = datetime.strptime(registro["prazo_entrega"], "%d/%m/%Y")
            return prazo.date() < datetime.now().date()
        except ValueError:
            return False

    def atualizar_tela(self):
        texto = self.busca.get().strip() if hasattr(self, "busca") else ""
        status = self.filtro_status.get() if hasattr(self, "filtro_status") else "Todos"
        servico = self.filtro_servico.get() if hasattr(self, "filtro_servico") else "Todos"
        registros = self.banco.buscar(texto, status, servico)

        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for registro in registros:
            valores = (
                registro["id"], registro["cliente"], registro["telefone"], registro["servico"],
                registro["data_pedido"], f"R$ {registro['valor']:.2f}", registro["prazo_entrega"],
                registro["status"], registro["observacoes"] or ""
            )
            tag = ("atrasado",) if self.pedido_atrasado(registro) else ()
            self.tabela.insert("", "end", values=valores, tags=tag)

        total, valor, pendentes = self.banco.resumo()
        self.resumo_label.config(
            text=f"Pedidos: {total}   |   Total: R$ {valor:.2f}   |   Pendentes: {pendentes}"
        )

    def limpar_filtros(self):
        self.busca.delete(0, tk.END)
        self.filtro_status.set("Todos")
        self.filtro_servico.set("Todos")
        self.atualizar_tela()

    def limpar_formulario(self):
        for campo in (self.cliente, self.telefone, self.valor, self.prazo, self.observacoes):
            campo.delete(0, tk.END)
        self.data_pedido.delete(0, tk.END)
        self.data_pedido.insert(0, self.data_hoje())
        self.servico.current(0)
        self.status.set("Recebido")
        self.pedido_selecionado = None
        for item in self.tabela.selection():
            self.tabela.selection_remove(item)


def iniciar():
    janela = tk.Tk()
    Aplicativo(janela)
    janela.mainloop()


if __name__ == "__main__":
    iniciar()
