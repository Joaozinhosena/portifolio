# Portfólio Flask — Module Code

Projeto Flask inspirado no HTML de referência enviado. O visual mantém o tema escuro, os destaques em roxo e as seções do modelo: Início, Sobre, Habilidades, Projetos e Contato.

## Tecnologias

- Python 3.12
- Flask
- Tailwind CSS 4 via Play CDN
- HTML + Jinja

Não há arquivos `.css` no projeto. As classes de estilo Tailwind estão diretamente em `templates/index.html`.

> **Nota sobre produção:** o Play CDN do Tailwind é prático para manter o projeto sem etapa de build e sem arquivo CSS, mas a documentação oficial recomenda esse CDN para desenvolvimento, não para produção. Esta versão prioriza a exigência de não criar arquivos CSS. Para um site de produção com maior desempenho, a alternativa é compilar Tailwind durante o deploy e gerar um CSS estático.

## Executar localmente

```bash
python -m venv .venv
```

Ative o ambiente virtual:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

Instale as dependências e rode o servidor:

```bash
pip install -r requirements.txt
python app.py
```

Abra `http://127.0.0.1:5000`.

## Personalização

Edite somente o dicionário `SITE` no começo de `app.py`:

- `name`, `brand_first`, `brand_last`: nome e marca do portfólio.
- `role_badge`, `headline`, `intro`: apresentação principal.
- `photo_url`: caminho da foto dentro de `public/`, por exemplo `/foto-perfil.jpg`.
- `resume_url`: caminho do currículo em PDF dentro de `public/`, por exemplo `/curriculo.pdf`.
- `about_title`, `about_text`, `stats`: seção Sobre e métricas.
- `skills`: habilidades, percentuais e cores.
- `projects`: cards e links dos seus projetos.
- `email`, `phone_display`, `phone_link` e `socials`: contato e redes.
- `testimonial`: depoimento exibido na página.

As métricas, o depoimento e os projetos que vêm preenchidos são exemplos de demonstração. Troque pelos seus dados reais antes de publicar.

Para imagens e PDFs, coloque os arquivos na pasta `public/`. A Vercel serve o conteúdo de `public/` diretamente pela CDN.

## Publicar na Vercel

A Vercel detecta aplicações Flask automaticamente quando encontra uma instância chamada `app` em `app.py` na raiz do projeto. Não é necessário `vercel.json` para esta estrutura.

1. Envie a pasta do projeto para um repositório GitHub.
2. Entre em [vercel.com/new](https://vercel.com/new) e importe o repositório.
3. Mantenha as configurações detectadas automaticamente e clique em **Deploy**.

Também é possível publicar usando a CLI da Vercel:

```bash
npm i -g vercel
vercel
vercel --prod
```

## Estrutura

```text
portfolio-flask/
├── app.py
├── requirements.txt
├── .python-version
├── .gitignore
├── README.md
├── public/
│   └── favicon.svg
└── templates/
    └── index.html
```
