Editar camada
===========

.. nota::
   Esta ação requer que o usuário pertença a um grupo com permissões de escrita.

* Para colocar uma camada em modo de edição seleccionamos no menu de acções, a entrada *" Editar camada "*. 
* Apenas uma camada por projeto pode ser colocada no modo de edição.  
* Durante a edição da camada, esta ficará bloqueada para não ser editada por outro usuário.
* Para ver as camadas que estão sendo editadas e, portanto, bloqueadas, você pode ver a entrada '*bloqueios*' na opção de 'serviços' do painel de controle. 

   :align: center

Quando você começa a editar, uma nova barra de ferramentas de edição é adicionada ao mapa, dependendo do tipo de geometria da camada, seja ponto, linha ou polígono.

.. image:: ../images/edition1_1.png
   :align: center

A barra de ferramentas de edição tem quatro opções para camadas de linha e polígono. A camada de pontos terá cinco opções:


.. image:: ../images/edition2.png
   :align: center

Adicionar um novo elemento à camada
----------------------------------
Para adicionar um novo elemento seleccione a ferramenta de desenho '*adicionar geometria*' (**1**) e depois desenhe o elemento no mapa (ponto, linha ou polígono). 

Uma vez desenhado o elemento, aparecerá um formulário na barra de navegação para que possamos introduzir os valores dos atributos do elemento.

.. image:: ../images/edition3.png
   :align: center
   
Se quisermos anexar qualquer ficheiro multimédia podemos fazê-lo a partir do separador *" Elemento de Recursos "*.

.. image:: ../images/edition4.png
   :align: center

Uma vez preenchido o formulário, seleccionaremos o botão *"Guardar"*. Nessa altura, o novo elemento e os recursos associados serão persistidos na base de dados.
Se pressionarmos o botão *"Cancelar"* a geometria será removida do mapa e o formulário será fechado.

Adicionar novo elemento (ponto) no centro do mapa
---------------------------------------------------
**Esta opção só estará ativa para editar camadas com geometrias de 'ponto'.**

Para utilizar esta ferramenta, selecionar o botão '*adicionar ponto no centro*' (**5**):

* Automaticamente uma cruz (+) aparecerá no centro da vista actual do mapa.
* Então, independentemente de onde você 'clicar' em qualquer parte do mapa, o ponto será sempre adicionado no centro da cruz.
* Você pode navegar ou mover o mapa para colocar a cruz na área desejada e assim adicionar o ponto.
* A outra opção é adicionar um ponto em nossa localização atual. Para isso é necessário utilizar o botão '*Obter posição atual*' (outra barra de ferramentas). O sistema, utilizando o GPS do computador ou dispositivo, centralizará o mapa com a localização detectada,
* Uma vez que o mapa esteja centralizado com a localização do gps, selecione o botão '*ponto adicionado no centro*' (**5**) e depois 'clique' para adicionar o novo elemento de ponto na localização atual.
* Adicionado o ponto aparecerá na *info* do painel de conteúdos o formulário para adicionar os atributos e recursos multimédia. 
* Finalmente na aba 'Detalhes do elemento' (aba onde são editados os atributos do novo elemento) clique em *salvar*.



Modificar um elemento existente
-------------------------------
Selecionar a ferramenta de '*elementos editados*' (**2**) na barra de edição. Em seguida, seleccione o elemento no mapa. Uma vez seleccionado o elemento, poderemos editar a sua geometria seleccionando e deslocando
os vértices no caso de se tratar de uma recta ou de um polígono, ou de um deslocamento do elemento no caso de se tratar de um ponto.

Um formulário com o valor dos atributos do elemento também será exibido na barra de navegação.

Depois de finalizada a modificação dos dados geométricos e/ou alfanuméricos do elemento, proceder como na seção anterior, selecionando o botão *"Salvar"*" ou *"Cancelar"*.

Eliminação de um elemento existente
------------------------------
Selecionar a ferramenta '*eliminar elementos*' (**3**) na barra de edição. Em seguida, seleccione o elemento que pretende remover no mapa. 

Depois de selecionado o elemento, na barra de navegação será mostrado um formulário com o valor dos atributos do elemento. No final deste formulário você encontrará o botão 'excluir' que será usado para excluir o elemento do mapa e do banco de dados.


Fechar edição
--------------
Finalmente, uma vez guardadas as alterações para cada elemento, clique no botão '*Edição completa*' (**4**) e a camada é desbloqueada para continuar a ser editada por outros utilizadores.

Uma vez terminada a edição, pode continuar a editar outras camadas, uma vez que enquanto a ferramenta para editar uma camada estiver aberta, o sistema não lhe permitirá editar uma segunda camada.
