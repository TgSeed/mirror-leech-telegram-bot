FROM anasty17/mltb:latest

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

COPY requirements.txt .
RUN python3 --version && python3 -m pip install -U pip && pip3 --version && pip3 uninstall crypto && pip3 uninstall pycrypto && \
 pip3 install pycryptodome pycryptodomex && pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
