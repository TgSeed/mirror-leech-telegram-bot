FROM anasty17/mltb:latest

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

COPY requirements.txt .
RUN python3 --version && python3 -m pip install --break-system-packages -U pip && pip3 --version && pip3 uninstall --break-system-packages crypto && pip3 uninstall --break-system-packages pycrypto && \
 pip3 install --break-system-packages pycryptodome pycryptodomex && pip3 install --break-system-packages --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
