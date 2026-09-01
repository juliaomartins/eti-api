"""
Build docs/erd.drawio from the erDiagram inside docs/database-schema.md.

    python docs/gen_erd.py

Generated rather than hand-drawn so the diagram and the data dictionary cannot
disagree. Edit the Mermaid block in database-schema.md, re-run this, commit both.

Layout: tables are placed in dependency layers so every relationship runs left
to right. The script refuses to write the file if any relationship would point
backwards -- one such edge drags a line across the whole canvas, which is what
made the first version unreadable.
"""
import pathlib
import re
import sys
from collections import defaultdict
from xml.sax.saxutils import quoteattr

RAIZ = pathlib.Path(__file__).resolve().parent
FONTE = RAIZ / 'database-schema.md'
ALVU = RAIZ / 'erd.drawio'

LARGURA, ALTU_TITULU, ALTU_LINHA, ALTU_NOTA, ESPASU_NOTA = 480, 32, 26, 30, 38
FOLIN = [46, 116, 176, 142]                       # key | type | name | comment

#: (column, row). A table only ever points at one in a higher column.
DISPOZISAUN = {
    'django_content_type':              (0, 0),
    'django_migrations':                (0, 1),
    'django_session':                   (0, 2),
    'accounts_user':                    (1, 0),
    'auth_group':                       (1, 1),
    'auth_permission':                  (1, 2),
    'attendance_listaprezensa':         (2, 0),
    'token_blacklist_outstandingtoken': (2, 1),
    'accounts_user_groups':             (2, 2),
    'accounts_user_user_permissions':   (2, 3),
    'auth_group_permissions':           (2, 4),
    'django_admin_log':                 (2, 5),
    'attendance_prezensa':              (3, 0),
    'token_blacklist_blacklistedtoken': (3, 1),
    'attendance_marka':                 (4, 0),
}
LINHA_Y = {0: [1060, 1330, 1570], 1: [40, 720, 880],
           2: [40, 330, 590, 770, 950, 1130], 3: [40, 430], 4: [40]}
KOLUNA_X = {0: 40, 1: 620, 2: 1200, 3: 1780, 4: 2360}

KOR = {'prezensa': ('#2D6A9F', '#1F4E79'), 'token': ('#7B4FA8', '#5C3580'),
       'django': ('#9AA0A6', '#5F6368')}
GRUPU = {'attendance_listaprezensa': 'prezensa', 'attendance_prezensa': 'prezensa',
         'attendance_marka': 'prezensa',
         'token_blacklist_outstandingtoken': 'token',
         'token_blacklist_blacklistedtoken': 'token'}

KARDINALIDADE = {'||': 'ERmandOne', '|o': 'ERzeroToOne', 'o|': 'ERzeroToOne',
                 '}o': 'ERzeroToMany', 'o{': 'ERzeroToMany',
                 '}|': 'ERoneToMany', '|{': 'ERoneToMany'}

ATRIBUTU = re.compile(r'^(?P<tipu>\S+)\s+(?P<naran>\w+)'
                      r'(?:\s+(?P<xave>PK|FK|UK))?(?:\s+"(?P<nota>[^"]*)")?$')
RELASAUN = re.compile(r'^(?P<a>\w+)\s+(?P<esq>\S{2})--(?P<dir>\S{2})\s+'
                      r'(?P<b>\w+)\s*:\s*"(?P<rotulu>[^"]*)"$')


def analiza(bloco):
    entidades, relasaun, atual, nota = [], [], None, None
    for bruta in bloco.splitlines():
        linha = bruta.strip()
        if not linha or linha == 'erDiagram':
            continue
        if linha.startswith('%%'):
            c = linha.lstrip('%').strip()
            if not c.startswith('----'):
                nota = c
            continue
        if atual is None and linha.endswith('{'):
            atual = {'naran': linha[:-1].strip(), 'atributu': [], 'nota': nota}
            nota = None
            continue
        if atual is not None:
            if linha == '}':
                entidades.append(atual); atual = None; continue
            m = ATRIBUTU.match(linha)
            if not m:
                sys.exit(f'unparsed attribute: {linha!r}')
            atual['atributu'].append(m.groupdict()); continue
        m = RELASAUN.match(linha)
        if not m:
            sys.exit(f'unparsed relationship: {linha!r}')
        relasaun.append(m.groupdict()); nota = None
    if atual is not None:
        sys.exit('unterminated entity block')
    return entidades, relasaun


def ponto(i, total):
    return round((i + 1) / (total + 1), 4)


def konstroi(entidades, relasaun, fatin):
    out, n = [], [0]

    def novo(p):
        n[0] += 1
        return f'{p}-{n[0]}'

    ids = {e['naran']: f'tbl-{e["naran"]}' for e in entidades}

    for e in entidades:
        naran = e['naran']
        x, y, altu = fatin[naran]
        isoladu = naran in ('django_migrations', 'django_session')
        if e['nota']:
            out.append(
                f'        <mxCell id={quoteattr(novo("note"))} value={quoteattr(e["nota"])} '
                'style="shape=note;whiteSpace=wrap;html=1;size=12;verticalAlign=middle;'
                'align=left;spacingLeft=8;fontSize=11;fontColor=#7A5C00;fillColor=#FFF8E1;'
                'strokeColor=#E6C200;" vertex="1" parent="1">\n'
                f'          <mxGeometry x="{x}" y="{y - ESPASU_NOTA}" width="{LARGURA}" '
                f'height="{ALTU_NOTA}" as="geometry" />\n        </mxCell>')
        out.append(
            f'        <mxCell id={quoteattr(ids[naran])} value={quoteattr(naran)} '
            'style="shape=table;startSize=32;container=1;collapsible=1;childLayout=tableLayout;'
            'fixedRows=1;rowLines=0;fontStyle=1;align=center;resizeLast=1;html=1;'
            f'fillColor={"#F0F0F0" if isoladu else "#E8EEF4"};'
            f'strokeColor={"#B0B0B0" if isoladu else "#2D6A9F"};'
            f'{"dashed=1;" if isoladu else ""}fontSize=13;fontColor=#1F3B54;shadow=1;" '
            'vertex="1" parent="1">\n'
            f'          <mxGeometry x="{x}" y="{y}" width="{LARGURA}" height="{altu}" '
            'as="geometry" />\n        </mxCell>')
        for i, a in enumerate(e['atributu']):
            rid = novo('row')
            out.append(
                f'        <mxCell id={quoteattr(rid)} value="" '
                'style="shape=tableRow;horizontal=0;startSize=0;swimlaneHead=0;swimlaneBody=0;'
                'fillColor=none;collapsible=0;dropTarget=0;points=[[0,0.5],[1,0.5]];'
                'portConstraint=eastwest;top=0;left=0;right=0;bottom=0;" '
                f'vertex="1" parent={quoteattr(ids[naran])}>\n'
                f'          <mxGeometry y="{ALTU_TITULU + i * ALTU_LINHA}" width="{LARGURA}" '
                f'height="{ALTU_LINHA}" as="geometry" />\n        </mxCell>')
            xave = a['xave'] or ''
            kor = {'PK': '#B85450', 'FK': '#2D6A9F', 'UK': '#7B4FA8'}.get(xave, '#333333')
            celulas = [(xave, f'fontStyle=1;fontColor={kor};align=center;'),
                       (a['tipu'], 'fontColor=#5F6368;align=left;spacingLeft=6;'),
                       (a['naran'], 'fontStyle=1;fontColor=#1F3B54;align=left;spacingLeft=6;'),
                       (a['nota'] or '', 'fontColor=#8A8A8A;fontStyle=2;align=left;spacingLeft=6;')]
            for j, (valor, estilu) in enumerate(celulas):
                out.append(
                    f'        <mxCell id={quoteattr(novo("cell"))} value={quoteattr(valor)} '
                    'style="shape=partialRectangle;connectable=0;fillColor=none;top=0;left=0;'
                    f'bottom=0;right=0;overflow=hidden;html=1;fontSize=11;{estilu}" '
                    f'vertex="1" parent={quoteattr(rid)}>\n'
                    f'          <mxGeometry x="{sum(FOLIN[:j])}" width="{FOLIN[j]}" '
                    f'height="{ALTU_LINHA}" as="geometry">\n'
                    f'            <mxRectangle width="{FOLIN[j]}" height="{ALTU_LINHA}" '
                    'as="alternateBounds" />\n          </mxGeometry>\n        </mxCell>')

    saida, entrada = defaultdict(list), defaultdict(list)
    for i, r in enumerate(relasaun):
        saida[r['a']].append(i); entrada[r['b']].append(i)
    for k in saida:
        saida[k].sort(key=lambda i: fatin[relasaun[i]['b']][1])
    for k in entrada:
        entrada[k].sort(key=lambda i: fatin[relasaun[i]['a']][1])

    for i, r in enumerate(relasaun):
        ini, fim = KARDINALIDADE.get(r['esq']), KARDINALIDADE.get(r['dir'])
        if ini is None or fim is None:
            sys.exit(f'unknown cardinality: {r["esq"]}--{r["dir"]}')
        kor, kor_txt = KOR[GRUPU.get(r['b'], 'django')]
        out.append(
            f'        <mxCell id={quoteattr(novo("edge"))} value={quoteattr(r["rotulu"])} '
            'style="edgeStyle=entityRelationEdgeStyle;rounded=1;html=1;'
            f'exitX=1;exitY={ponto(saida[r["a"]].index(i), len(saida[r["a"]]))};exitDx=0;exitDy=0;'
            f'entryX=0;entryY={ponto(entrada[r["b"]].index(i), len(entrada[r["b"]]))};'
            f'entryDx=0;entryDy=0;startArrow={ini};startFill=0;endArrow={fim};endFill=0;'
            f'strokeColor={kor};strokeWidth=1.5;fontSize=11;fontColor={kor_txt};'
            'labelBackgroundColor=#FFFFFF;jettySize=28;" edge="1" parent="1" '
            f'source={quoteattr(ids[r["a"]])} target={quoteattr(ids[r["b"]])}>\n'
            '          <mxGeometry relative="1" as="geometry" />\n        </mxCell>')

    out.append(
        '        <mxCell id="titulu" value="&lt;b&gt;ETI PREZENSA — database schema'
        '&lt;/b&gt;&lt;br&gt;&lt;font style=&quot;font-size:11px&quot;&gt;'
        'generated from docs/database-schema.md by docs/gen_erd.py&lt;/font&gt;" '
        'style="text;html=1;align=left;verticalAlign=middle;fontSize=20;fontColor=#1F3B54;" '
        'vertex="1" parent="1">\n          <mxGeometry x="620" y="-120" width="900" '
        'height="60" as="geometry" />\n        </mxCell>')
    out.append(
        '        <mxCell id="legenda" value="&lt;b&gt;How to read this&lt;/b&gt;&lt;br&gt;'
        '&lt;font color=&quot;#B85450&quot;&gt;PK&lt;/font&gt; primary key &amp;#183; '
        '&lt;font color=&quot;#2D6A9F&quot;&gt;FK&lt;/font&gt; foreign key &amp;#183; '
        '&lt;font color=&quot;#7B4FA8&quot;&gt;UK&lt;/font&gt; unique&lt;br&gt;'
        '&lt;font color=&quot;#2D6A9F&quot;&gt;──&lt;/font&gt; attendance &amp;#183; '
        '&lt;font color=&quot;#7B4FA8&quot;&gt;──&lt;/font&gt; JWT tokens &amp;#183; '
        '&lt;font color=&quot;#9AA0A6&quot;&gt;──&lt;/font&gt; Django plumbing&lt;br&gt;'
        'Crow\'s foot = many &amp;#183; single bar = exactly one&lt;br&gt;'
        'Yellow notes carry composite UNIQUE constraints&lt;br&gt;'
        'Dashed tables have no foreign keys" '
        'style="rounded=1;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacingLeft=10;'
        'spacingTop=6;fontSize=11;fillColor=#FBFBFB;strokeColor=#C4C4C4;" '
        'vertex="1" parent="1">\n          <mxGeometry x="40" y="-120" width="480" '
        'height="130" as="geometry" />\n        </mxCell>')

    return ('<mxfile host="app.diagrams.net" agent="eti-api docs" type="device">\n'
            '  <diagram id="eti-prezensa-erd" name="ETI PREZENSA — ERD">\n'
            '    <mxGraphModel dx="2200" dy="1400" grid="1" gridSize="10" guides="1" '
            'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
            'pageWidth="3300" pageHeight="2339" math="0" shadow="0">\n      <root>\n'
            '        <mxCell id="0" />\n        <mxCell id="1" parent="0" />\n'
            + '\n'.join(out) +
            '\n      </root>\n    </mxGraphModel>\n  </diagram>\n</mxfile>\n')


def main():
    bloco = re.search(r'```mermaid\n(.*?)\n```', FONTE.read_text(encoding='utf-8'), re.S)
    if not bloco:
        sys.exit('no mermaid block in database-schema.md')
    entidades, relasaun = analiza(bloco.group(1))

    faltando = {e['naran'] for e in entidades} - set(DISPOZISAUN)
    if faltando:
        sys.exit(f'entities missing from the layout: {sorted(faltando)}')
    fatin = {e['naran']: (KOLUNA_X[DISPOZISAUN[e['naran']][0]],
                          LINHA_Y[DISPOZISAUN[e['naran']][0]][DISPOZISAUN[e['naran']][1]],
                          ALTU_TITULU + ALTU_LINHA * len(e['atributu']))
             for e in entidades}
    tras = [f'{r["a"]} -> {r["b"]}' for r in relasaun
            if DISPOZISAUN[r['a']][0] >= DISPOZISAUN[r['b']][0]]
    if tras:
        sys.exit(f'these relationships point backwards: {tras}')

    ALVU.write_text(konstroi(entidades, relasaun, fatin), encoding='utf-8')
    print(f'entities      {len(entidades)}')
    print(f'attributes    {sum(len(e["atributu"]) for e in entidades)}')
    print(f'relationships {len(relasaun)}  (all left-to-right)')
    print(f'written       {ALVU}')


if __name__ == '__main__':
    main()
