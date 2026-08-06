FROM mcr.microsoft.com/playwright/python:v1.62.0-jammy

WORKDIR /app

COPY SFL_Automation/requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY SFL_Automation/ .

EXPOSE 10000

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=10000", "--server.address=0.0.0.0"]
