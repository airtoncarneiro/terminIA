webui empacotado com ollama: docker run -d -p 3000:8080 --gpus=all -v ollama:/root/.ollama -v open-webui:/app/backend/data --name open-webui --restart always ghcr.io/open-webui/open-webui:ollama


----

para subir o serviço na pasta onde está o arquivo:

docker compose up -d



Sobre a GPU no Ubuntu

Para que o bloco de GPU acima funcione, você precisa:

Ter drivers Nvidia instalados no host.

Ter o Nvidia Container Toolkit configurado (substituto do antigo nvidia-docker2).

No /etc/docker/daemon.json, normalmente ter algo assim (se ainda não tiver):


{
  "default-runtime": "nvidia",
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  }
}



sudo systemctl restart docker




Como validar que a GPU está sendo usada

Depois que o serviço estiver no ar:

docker exec -it open-webui nvidia-smi



For Nvidia GPU support, you change the image from ghcr.io/open-webui/open-webui:main to ghcr.io/open-webui/open-webui:cuda and add the following to your service definition in the docker-compose.yml file: https://docs.openwebui.com/getting-started/quick-start/
