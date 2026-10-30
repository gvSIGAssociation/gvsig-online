# -*- coding: utf-8 -*-
"""Lee la definición de cada nodo en TableShape.js y en la paleta de etl.html.

Lo usan el comando de scaffold y los tests del catálogo. No importa Django.
"""

import os
import re

_PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TABLESHAPE_PATH = os.path.join(_PKG, 'static', 'js', 'TableShape.js')
PALETTE_PATH = os.path.join(_PKG, 'templates', 'etl.html')

_NODE_RE = re.compile(
    r'^([A-Za-z_][A-Za-z0-9_]*) = draw2d\.shape\.layout\.VerticalLayout\.extend\(\{',
    re.M,
)
_PORT_RE = re.compile(r'createPort\(\s*["\'](input|output)["\']\s*\)')
_PARAM_RE = re.compile(r'"parameters"\s*:\s*\[')
_KEY_RE = re.compile(r"""['"]([A-Za-z0-9_-]+)['"]\s*:""")
_TEXT_RE = re.compile(
    r'text\s*:\s*(?:gettext\(\s*)?["\']([^"\']+)["\']'
)
_DB_TYPE_RE = re.compile(r"dbc\[i\]\.type\s*==\s*'([^']+)'")
_SHAPE_RE = re.compile(
    r'data-shape="([^"]+)"[^>]*>(.*?)</a>',
    re.S,
)
_TRANS_RE = re.compile(r"""\{%\s*trans\s+(['"])(.*?)\1\s*%\}""", re.S)


def read_tableshape(path=None):
    with open(path or TABLESHAPE_PATH, 'r', encoding='utf-8') as handle:
        return handle.read()


def read_palette(path=None):
    with open(path or PALETTE_PATH, 'r', encoding='utf-8') as handle:
        return handle.read()


def split_node_blocks(source):
    """Devuelve [(nombre, bloque), ...] en el orden del fichero."""
    matches = list(_NODE_RE.finditer(source))
    blocks = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(source)
        blocks.append((match.group(1), source[start:end]))
    return blocks


def node_block(source, type_name):
    for name, block in split_node_blocks(source):
        if name == type_name:
            return block
    raise KeyError(type_name)


def count_ports(block):
    inputs = 0
    outputs = 0
    for match in _PORT_RE.finditer(block):
        if match.group(1) == 'input':
            inputs += 1
        else:
            outputs += 1
    return inputs, outputs


def _balanced_object(text, open_brace):
    """Texto del objeto `{...}` que empieza en open_brace, respetando cadenas."""
    depth = 0
    quote = None
    escaped = False
    for index in range(open_brace, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ('"', "'"):
            quote = char
            continue
        if char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                return text[open_brace:index + 1]
    return text[open_brace:]


def _object_keys(text, open_brace):
    obj = _balanced_object(text, open_brace)
    keys = []
    for key in _KEY_RE.findall(obj):
        if key not in keys:
            keys.append(key)
    return keys


def parameter_keys(block):
    """Claves del último objeto `parameters` anterior a addEntity (el de Aceptar)."""
    head = block.split('addEntity:', 1)[0]
    found = []
    merged_extra = False
    for match in _PARAM_RE.finditer(head):
        cursor = match.end()
        while cursor < len(head) and head[cursor] in ' \t\r\n':
            cursor += 1
        if cursor >= len(head):
            continue
        if head.startswith('Object.assign', cursor):
            brace = head.find('{', cursor)
            if brace == -1:
                continue
            keys = _object_keys(head, brace)
            window = head[cursor:cursor + 1200]
            if 'formatParams' in window:
                extra = _last_assigned_object_keys(head[:match.start()], 'formatParams')
                for key in extra:
                    if key not in keys:
                        keys.append(key)
            merged_extra = True
        elif head[cursor] == '{':
            keys = _object_keys(head, cursor)
            merged_extra = False
        else:
            continue
        if keys:
            found = keys
    if not merged_extra:
        return found
    return found


def _last_assigned_object_keys(text, var_name):
    """Claves del último `var_name = { ... }` que no esté comentado."""
    pattern = re.compile(re.escape(var_name) + r'\s*=\s*\{')
    keys = []
    for match in pattern.finditer(text):
        line_start = text.rfind('\n', 0, match.start()) + 1
        if text[line_start:match.start()].strip().startswith('//'):
            continue
        keys = _object_keys(text, match.end() - 1)
    return keys


def _add_entity_source(block):
    match = re.search(r'\n[ \t]*addEntity:\s*function', block)
    if not match:
        return ''
    start = match.start()
    nxt = re.search(r'\n[ \t]*removeEntity:\s*function', block[start + 10:])
    end = start + 10 + nxt.start() if nxt else len(block)
    return block[start:end]


def port_specs(block):
    """Puertos en el orden de createPort dentro de addEntity, con su etiqueta."""
    source = _add_entity_source(block) or block
    labels = {}
    for match in re.finditer(
        r'(\w+)\s*=\s*new draw2d\.shape\.basic\.Label\(\{',
        source,
    ):
        window = source[match.end():match.end() + 500]
        text = _TEXT_RE.search(window)
        if text:
            labels[match.group(1)] = text.group(1)
    ports = []
    for match in re.finditer(
        r'(\w+)\.createPort\(\s*["\'](input|output)["\']\s*\)',
        source,
    ):
        ports.append({
            'direction': match.group(2),
            'label': labels.get(match.group(1), ''),
        })
    if not ports:
        inputs, outputs = count_ports(block)
        ports = (
            [{'direction': 'input', 'label': 'Input'} for _ in range(inputs)]
            + [{'direction': 'output', 'label': 'Output'} for _ in range(outputs)]
        )
    return ports


def connection_types(block):
    found = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith('//') or stripped.startswith('*'):
            continue
        for name in _DB_TYPE_RE.findall(line):
            if name not in found:
                found.append(name)
    return found


def _choices_for(block, param):
    if param.startswith('get_'):
        return []
    token = re.escape(param) + r"-'\+ID\+'"
    select = re.search(
        r'<(select|div)[^>]*(?:id|name)=["\']' + token + r'["\'][\s\S]{0,1800}?</\1>',
        block,
    )
    window = select.group(0) if select else ''
    if not window:
        radio = re.search(
            r'name=["\']' + token + r'["\'][\s\S]{0,900}?name=["\'](?!' + token + r')',
            block,
        )
        window = radio.group(0) if radio else ''
    if not window:
        return []
    values = re.findall(r'value\s*=\s*["\']([^"\']*)["\']', window)
    cleaned = []
    for value in values:
        value = value.strip()
        if not value or value in cleaned or 'ID' in value:
            continue
        cleaned.append(value)
    if len(cleaned) < 2 or len(cleaned) > 16:
        return []
    return cleaned


def palette_labels(html=None):
    html = html if html is not None else read_palette()
    labels = {}
    for shape, raw in _SHAPE_RE.findall(html):
        text = _TRANS_RE.sub(lambda m: m.group(2), raw)
        text = re.sub(r'\s+', ' ', text).strip()
        labels[shape] = text
    return labels


def parse_node(name, block, label=''):
    keys = parameter_keys(block)
    ports = port_specs(block)
    inputs, outputs = count_ports(block)
    # El test compara con el bloque entero. Si addEntity no concentra todos
    # los createPort, se avisa con el recuento del bloque.
    if len(ports) != inputs + outputs:
        ports = (
            [{'direction': 'input', 'label': 'Input'} for _ in range(inputs)]
            + [{'direction': 'output', 'label': 'Output'} for _ in range(outputs)]
        )
    parameters = []
    for key in keys:
        item = {'name': key}
        summary = _param_summary(key)
        if summary:
            item['summary'] = summary
        choices = _choices_for(block, key)
        if choices:
            item['choices'] = choices
        if key in ('db', 'db-option', 'api') or key.endswith('-file'):
            item['required'] = True
        parameters.append(item)
    connection_parameter = None
    for candidate in ('db-option', 'db', 'api'):
        if candidate in keys:
            connection_parameter = candidate
            break
    sql_parameters = [key for key in keys if key in ('clause', 'sql', 'query')]
    return {
        'type': name,
        'label': label or name,
        'family': _family(name),
        'summary': '',
        'parameters': parameters,
        'ports': ports,
        'connection_types': connection_types(block),
        'connection_parameter': connection_parameter,
        'sql_parameters': sql_parameters,
    }


def parse_all(source=None, html=None):
    source = source if source is not None else read_tableshape()
    labels = palette_labels(html)
    return [
        parse_node(name, block, labels.get(name, name))
        for name, block in split_node_blocks(source)
    ]


def _family(name):
    if name.startswith('input_'):
        return 'input'
    if name.startswith('output_'):
        return 'output'
    if name.startswith('crea_'):
        return 'creator'
    return 'transform'


def _param_summary(key):
    labels = {
        'db': 'Nombre de la conexión.',
        'db-option': 'Nombre de la conexión.',
        'api': 'Nombre de la conexión.',
        'schema-name': 'Esquema.',
        'schema-name-option': 'Esquema de destino.',
        'get_schema-name': 'Esquemas cargados en el desplegable. Lo rellena el servidor al aplicar.',
        'get_schema-name-option': 'Esquemas cargados en el desplegable.',
        'tablename': 'Tabla.',
        'get_tablename': 'Tablas cargadas en el desplegable.',
        'table-name': 'Tabla.',
        'get_table-name': 'Tablas cargadas en el desplegable.',
        'owner-name': 'Esquema (owner) de Oracle.',
        'checkbox': 'Si es verdadero, se usa SQL libre en lugar de la tabla.',
        'clause': 'Cláusula SQL adicional (WHERE, etc.).',
        'sql': 'Consulta SQL.',
        'query': 'Sentencia SQL.',
        'attr': 'Atributo sobre el que actúa la tarea.',
        'expression': 'Expresión de cálculo.',
        'filter-expression': 'Expresión compuesta del filtro.',
        'operation': 'Modo de escritura.',
        'epsg': 'Código EPSG.',
        'source-epsg': 'EPSG de origen.',
        'target-epsg': 'EPSG de destino.',
    }
    return labels.get(key, '')
