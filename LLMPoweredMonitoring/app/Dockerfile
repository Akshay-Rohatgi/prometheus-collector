FROM python:3.12-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y gcc apt-transport-https ca-certificates curl gnupg git  && rm -rf /var/lib/apt/lists/*

# install kubectl
RUN curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl" && \
    chmod +x kubectl && mv kubectl /usr/local/bin/

# install helm
RUN curl -fsSL https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
# add prometheus-community repository
RUN helm repo add prometheus-community https://prometheus-community.github.io/helm-charts

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos '' appuser && chown -R appuser:appuser /app
USER appuser

# set environment variables
ENV DEBUG_MODE true
ENV ENABLE_FILE_LOGGING false

EXPOSE 8000

CMD ["python", "main.py"]