# -*- coding: utf-8 -*-
"""Argumentos tipados de las herramientas del asistente.

El modelo recibe la forma exacta de una propuesta o de una pregunta, en lugar de
tener que escribir un JSON dentro de un texto, que es lo que más fallos daba.
proposal_json y questions_json se siguen aceptando. La validación de contenido
(tipos de nodo, conexiones, puertos...) sigue siendo la de graph.py y questions.py:
aquí solo se describe la forma, y por eso casi todo es opcional.
"""

import json
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

INVALID_ARGUMENTS = ('Los argumentos no tienen la forma esperada. Revisa los campos y vuelve a llamar a la herramienta '
                     'con la propuesta o las preguntas completas.')


class _Open(BaseModel):
    model_config = ConfigDict(extra='allow', populate_by_name=True)


class NodeIn(_Open):
    id: Optional[str] = Field(None, description='Id del nodo: n1, n2... Los nuevos, a partir del siguiente id libre.')
    type: Optional[str] = Field(None, description='Tipo del catálogo, por ejemplo trans_Filter.')
    label: Optional[str] = Field(None, description='Nombre visible del nodo.')
    parameters: Optional[Dict[str, Any]] = Field(None, description='Parámetros, con los nombres y formatos de su ficha.')
    schema_: Optional[List[Any]] = Field(None, alias='schema', description='Columnas de salida, si se conocen.')
    schemaold: Optional[List[Any]] = None


class EdgeIn(_Open):
    source: Optional[str] = Field(None, description='Id del nodo de origen.')
    target: Optional[str] = Field(None, description='Id del nodo de destino.')
    source_port: int = Field(0, description='Salida del origen, desde 0.')
    target_port: int = Field(0, description='Entrada del destino, desde 0.')


class OperationIn(EdgeIn):
    op: Optional[Literal['add_node', 'update_node', 'remove_node', 'add_edge', 'remove_edge']] = None
    node: Optional[NodeIn] = Field(None, description='El nodo, en add_node.')
    id: Optional[str] = Field(None, description='Id del nodo, en update_node y remove_node.')
    label: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = Field(None, description='Solo los parámetros que cambian, en update_node.')


class ProposalArgs(BaseModel):
    mode: Optional[Literal['replace', 'patch']] = Field(
        None, description='replace rehace el flujo (nodes y edges); patch modifica el actual (ops).')
    name: Optional[str] = Field(None, description='Nombre del flujo.')
    description: Optional[str] = Field(None, description='Descripción del flujo.')
    assumptions: Optional[List[Any]] = Field(None, description='Decisiones tomadas, una frase por decisión.')
    nodes: Optional[List[NodeIn]] = Field(None, description='Con mode replace: todos los nodos.')
    edges: Optional[List[EdgeIn]] = Field(None, description='Con mode replace: todas las conexiones.')
    ops: Optional[List[OperationIn]] = Field(None, description='Con mode patch: las operaciones, en orden.')
    proposal_json: Optional[str] = Field(None, description='Alternativa: la propuesta entera como texto JSON.')


class QuestionIn(_Open):
    label: Optional[str] = Field(None, description='Etiqueta corta, por ejemplo "Campo de cruce".')
    text: Optional[str] = Field(None, description='La pregunta.')
    source: Optional[str] = Field(None, description='De dónde salen las opciones: choices, connections, datastores, '
                                                    'tables, columns, files, workspaces, layer_groups o custom.')
    node: Optional[str] = Field(None, description='Id del nodo, si es un parámetro de un nodo.')
    param: Optional[str] = Field(None, description='Parámetro del nodo.')
    type: Optional[str] = Field(None, description='Tipo de nodo, si aún no está en el canvas.')
    multiple: Optional[bool] = Field(None, description='True si puede elegir varias.')
    options: Optional[List[Any]] = Field(None, description='Con custom: hasta 8 textos cortos.')
    connection: Optional[str] = None
    schema_: Optional[str] = Field(None, alias='schema')
    table: Optional[str] = None
    extensions: Optional[Any] = Field(None, description='Con files: extensiones, por ejemplo "shp".')
    file: Optional[str] = Field(None, description='Con columns: el valor file:// del fichero.')
    sheet: Optional[str] = None


class AskArgs(BaseModel):
    questions: Optional[List[QuestionIn]] = Field(None, description='Hasta 4 preguntas.')
    questions_json: Optional[str] = Field(None, description='Alternativa: las preguntas como texto JSON.')


def plain(value):
    """Modelos Pydantic a diccionarios, con los nombres que usa el validador."""
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=True, exclude_none=True)
    if isinstance(value, list):
        return [plain(item) for item in value]
    return value


def proposal_payload(proposal_json, **fields):
    """Propuesta a partir de los argumentos. Lanza ValueError si proposal_json no es JSON."""
    if (proposal_json or '').strip():
        try:
            return json.loads(proposal_json)
        except (TypeError, ValueError):
            raise ValueError('proposal_json no es JSON válido.')
    return {key: plain(value) for key, value in fields.items() if value is not None}
