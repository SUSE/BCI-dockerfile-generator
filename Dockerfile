FROM ghcr.io/dcermak/bci-ci:latest

RUN mkdir /src/
WORKDIR /src/
COPY . .

RUN poetry install

ENTRYPOINT ["poetry", "run"]
