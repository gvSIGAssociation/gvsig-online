1. Introdução
===============

**gvSIG Online** é uma plataforma integral para a implementação de Infraestruturas de Dados Espaciais (IDE), 100% com software livre.

Uma solução rápida e poderosa para colocar em movimento a infra-estrutura necessária para gerenciar da maneira mais eficiente os dados espaciais de uma organização.

gvSIG Online permite compartilhar informações geográficas na nuvem, gerar mapas e aplicações através de ferramentas simples e poderosas de administração do sistema. Bases de dados, geoportais, aplicações móveis, GIS Desktop... todos os componentes numa solução integral, livre e interoperável.


1.2  Características
-------------------

*   **Solução integral**: BD, geoportal, SIG desktop, aplicativo móvel...

*   Abordagem **orientada para o serviço**, adaptada às necessidades do cliente.

*   **Software livre** e tecnologias maduras.

*   **Basado em padrões**: WMS, WFS, â€¦

*   Design rápido, simples e **atraente**.

*   Escalável e adaptável às necessidades do cliente.

*   Sem restrições de qualquer tipo: usuários, downloads, camadas, â€¦

*   Cumpre com a legislação INSPIRE, LISIGE...


1.3 Baseado na arquitetura IDE
------------------------------

A Infraestrutura de Dados Espaciais (IDE) é um sistema informático integrado por un conjunto de recursos (catálogos, servidores, programas, aplicações, páginas web,â€¦), 
que permite o acceso e gestão de conjuntos de dados e serviços geográficos (descritos através dos seus metadatos), disponíveis na Internet, 
que cumpre uma série de regras, normas e especificações que regulam e asseguram a interoperabilidade da informação geográfica.

A arquitectura IDE é baseado no modelo clássico de três camadas: apresentação, aplicação e dados.

*	Na **camada de apresentação** teremos as aplicações que permitirão ao usuário interagir com a informação geográfica. Esta é a face vísivel da IDE, como a aplicação geoportal ou a aplicação móvel.

*	Na **camada de aplicação** teremos o servidor de mapas Geoserver que nos permitirá¡ oferecer dados através de protocolos pradão para acesso a mapas (WMS), mapas tesselação (WMTS), objetos geogrÃ¡ficos (WFS) ou cobertura (WCS).

*	Finalmente, na **camada de dados**  vamos centralizar os dados no banco de dados geoespaciais PostGIS e as informações sobre os usuários do sistema no banco de dados OpenLDAP.

.. image:: ../images/img_arquitectura.png
    :align: center

1.4 Licença
------------

gvSIG Online é distribuído sob licença AGPL:

*   **Affero** (Transposição da GPL para aplicações web)

    `https://es.wikipedia.org/wiki/GNU_Affero_General_Public_License <https://es.wikipedia.org/wiki/GNU_Affero_General_Public_License>`_
