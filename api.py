from flask import Flask, jsonify, request

import banco


app = Flask(__name__)


@app.route("/api/ocorrencias", methods=["GET"])
def obter_ocorrencias():
    # Filtros opcionais por período: ?de=AAAA-MM-DD&ate=AAAA-MM-DD (datas da ocorrência, inclusive)
    de = request.args.get("de")
    ate = request.args.get("ate")

    ocorrencias = banco.listar_ocorrencias()

    dados = []

    for ocorrencia in ocorrencias:
        if de and ocorrencia["data_ocorrencia"] < de[:10]:
            continue

        if ate and ocorrencia["data_ocorrencia"] > ate[:10]:
            continue

        dados.append({
            "id_ocorrencia": ocorrencia["id_ocorrencia"],
            "data_ocorrencia": ocorrencia["data_ocorrencia"],
            "hora_ocorrencia": ocorrencia["hora_ocorrencia"],
            "produto": ocorrencia["numero_serie_produto"],
            "modelo_produto": ocorrencia["modelo_produto"],
            "tipo_defeito": ocorrencia["nome_tipo_defeito"],
            "estacao": ocorrencia["nome_estacao"],
            "maquina": ocorrencia["nome_maquina"],
            "usuario": ocorrencia["nome_usuario"],
            "classificacao_defeito": ocorrencia["classificacao_defeito"],
            "situacao_produto": ocorrencia["situacao_produto"],
            "observacao_ocorrencia": ocorrencia["observacao_ocorrencia"],
            "acao_realizada": ocorrencia["acao_realizada"],
            "status_ocorrencia": ocorrencia["status_ocorrencia"]
        })

    return jsonify(dados)


@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({
        "sistema": "Controle da Qualidade",
        "status": "online"
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False
    )