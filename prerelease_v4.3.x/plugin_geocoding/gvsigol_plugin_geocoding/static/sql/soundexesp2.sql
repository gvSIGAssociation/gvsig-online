-- Modification of soundexesp script to allow for using strings with more than one word
CREATE OR REPLACE FUNCTION soundexesp2(INPUT text) RETURNS text
IMMUTABLE STRICT COST 500 LANGUAGE plpgsql
AS $$
DECLARE
	soundex text='';
	soundexaux text= '';	
	-- para determinar la primera letra
	pri_letra text;
	resto text;
	sustituida text ='';
	-- para quitar adyacentes
	anterior text;
	actual text;
	corregido text;
	inputaux text;
	inputArray text[];
BEGIN
       -- devolver null si recibi un string en blanco o con espacios en blanco
	IF LENGTH(TRIM(INPUT))= 0 THEN
		RETURN NULL;
	END IF;
 
 	inputaux = INPUT; 	
 	inputArray = regexp_split_to_array(inputaux, E'\\s+');
 
 	FOR j IN 0 .. array_length(inputArray,1) LOOP
 		INPUT = inputArray[j];
		-- 1: LIMPIEZA:
			-- pasar a mayuscula, eliminar la letra "H" inicial, los acentos y la enie
			-- 'holá coñó' => 'OLA CONO'
			INPUT=translate(ltrim(TRIM(UPPER(INPUT)),'H'),'ÑÁÉÍÓÚÀÈÌÒÙÜ','NAEIOUAEIOUU');
	 
			-- eliminar caracteres no alfabéticos (números, símbolos como &,%,",*,!,+, etc.
			INPUT=regexp_replace(INPUT, '[^a-zA-Z]', '', 'g');
	 
		-- 2: PRIMERA LETRA ES IMPORTANTE, DEBO ASOCIAR LAS SIMILARES
		--  'vaca' se convierte en 'baca'  y 'zapote' se convierte en 'sapote'
		-- un fenomeno importante es GE y GI se vuelven JE y JI; CA se vuelve KA, etc
		pri_letra =substr(INPUT,1,1);
		resto =substr(INPUT,2);
		CASE 
			WHEN pri_letra IN ('V') THEN
				sustituida='B';
			WHEN pri_letra IN ('Z','X') THEN
				sustituida='S';
			WHEN pri_letra IN ('G') AND substr(INPUT,2,1) IN ('E','I') THEN
				sustituida='J';
			WHEN pri_letra IN('C') AND substr(INPUT,2,1) NOT IN ('H','E','I') THEN
				sustituida='K';
			ELSE
				sustituida=pri_letra;
	 
		END CASE;
		--corregir el parametro con las consonantes sustituidas:
		INPUT=sustituida || resto;		
	 
		-- 3: corregir "letras compuestas" y volverlas una sola
		INPUT=REPLACE(INPUT,'CH','V');
		INPUT=REPLACE(INPUT,'QU','K');
		INPUT=REPLACE(INPUT,'LL','J');
		INPUT=REPLACE(INPUT,'CE','S');
		INPUT=REPLACE(INPUT,'CI','S');
		INPUT=REPLACE(INPUT,'YA','J');
		INPUT=REPLACE(INPUT,'YE','J');
		INPUT=REPLACE(INPUT,'YI','J');
		INPUT=REPLACE(INPUT,'YO','J');
		INPUT=REPLACE(INPUT,'YU','J');
		INPUT=REPLACE(INPUT,'GE','J');
		INPUT=REPLACE(INPUT,'GI','J');
		INPUT=REPLACE(INPUT,'NY','N');
		-- para debug:    --return input;
	 
		-- EMPIEZA EL CALCULO DEL SOUNDEX
		-- 4: OBTENER PRIMERA letra
		pri_letra=substr(INPUT,1,1);
	 
		-- 5: retener el resto del string
		resto=substr(INPUT,2);
	 
		--6: en el resto del string, quitar vocales y vocales fonéticas
		resto=translate(resto,'@AEIOUHWY','@');
	 
		--7: convertir las letras foneticamente equivalentes a numeros  (esto hace que B sea equivalente a V, C con S y Z, etc.)
		resto=translate(resto, 'BPFVCGKSXZDTLMNRQJ', '111122222233455677');
		-- así va quedando la cosa
		soundex=pri_letra || resto;
	 
		--8: eliminar números iguales adyacentes (A11233 se vuelve A123)
		anterior=substr(soundex,1,1);
		corregido=anterior;

		IF soundex != '' THEN
			FOR i IN 2 .. LENGTH(soundex) LOOP
				actual = substr(soundex, i, 1);
				IF actual <> anterior THEN
					corregido=corregido || actual;
					anterior=actual;			
				END IF;
			END LOOP;
			-- así va la cosa
			soundex=corregido;
		 
			-- 9: siempre retornar un string de 4 posiciones
			soundex=rpad(soundex,4,'0');
			soundex=substr(soundex,1,4);	
			
			soundexaux = soundexaux || soundex || ' ';
		END IF;
	END LOOP;	
 
	-- YA ESTUVO
	RETURN TRIM(soundexaux);	
END;	
$$