class AddQuery:
    WEB_VIEW_BASE_INFO = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 17, 18, 19, 20, 21]
    WEB_VIEW_COMPOSITES = [["Параметры синтеза:", ["Параметр", "Еденица измерения", "Значение"]], ["Параметры измерений:", ["Параметр", "Еденица измерения", "Значение"]], ["Ингредиенты:", ["Ингредиент"]], ["Ключевые слова:", ["Ключевое слово"]], ["Страны публикации:", ["Страна"]]]
    WEB_VIEW_COMPOSITES_COL_POS = {12: 0, 13: 1, 14: 2, 15: 3, 16: 4}
    DATA_DICT_MAIN_ID = {"productID": 1, "doi": 2, "year": 14, "journal": 15}
    DATA_DICT_MAIN_STRUCT = {"product": 0, "productID": 1, "doi": 2, "a_param": 3, "mix_method": 4, "mix_time": 5, "method": 6, "gas": 7, "synth_time": 8, "feature": 9, "contributor": 10, "comment": 11, "cipher": 12, "url": 13, "year": 14, "journal": 15, "impact": 16}

    def getAddCols(self) -> tuple[list, list[list]]:
        return AddQuery.WEB_VIEW_BASE_INFO, AddQuery.WEB_VIEW_COMPOSITES, AddQuery.WEB_VIEW_COMPOSITES_COL_POS
    
    def form_insert_queries_sub(dataDict: dict) -> list[str]:
        
        outQueries = []

        main = dataDict.get("main")
        pid = main[AddQuery.DATA_DICT_MAIN_ID["productID"]]
        doi = main[AddQuery.DATA_DICT_MAIN_ID["doi"]]

        key_words = dataDict.get("Ключевые слова:")
        if key_words and doi:
            for row in key_words:
                keyWrd = "INSERT INTO key_word(DOI, WORD) VALUES ('{DOI}', '{WORD}');".format(DOI = doi, WORD = row[0])
                outQueries.append(keyWrd)

        ings = dataDict.get("Ингредиенты:")
        if ings and pid:
            for row in ings:
                indredients = "INSERT INTO ingredients(PRODUCT_ID, INGREDIENT) VALUES ({PRODUCT_ID}, '{INGREDIENT}');".format(PRODUCT_ID = pid, INGREDIENT = row[0])
                outQueries.append(indredients)

        countries = dataDict.get("Страны публикации:")
        if countries and doi:
            for row in countries:
                count = "INSERT INTO countries(DOI, COUNTRY) VALUES ('{DOI}', '{COUNTRY}');".format(DOI = doi, COUNTRY = row[0])
                outQueries.append(count)

        meas = dataDict.get("Параметры измерений:")
        if meas and pid:
            for row in meas:
                if row[0]:
                    val_min, val_max = AddQuery.decompose_range(row[2])
                    measurement = "INSERT INTO measurements(PRODUCT_ID, MEASURED_PARAMETER, MEASURED_UNIT, MEASURED_MIN_VALUE, MEASURED_MAX_VALUE) VALUES ({PRODUCT_ID}, '{MEASURED_PARAMETER}', '{MEASURED_UNIT}', {MEASURED_MIN_VALUE}, {MEASURED_MAX_VALUE});".format(
                        PRODUCT_ID = pid,
                        MEASURED_PARAMETER = row[0],
                        MEASURED_UNIT = row[1],
                        MEASURED_MIN_VALUE = val_min,
                        MEASURED_MAX_VALUE = val_max
                    )
                    outQueries.append(measurement)

        synth = dataDict.get("Параметры синтеза:")
        if synth and pid:
            for row in synth:
                if row[0]:
                    val_min, val_max = AddQuery.decompose_range(row[2])
                    parameter = "INSERT INTO synthesis_parameter(PRODUCT_ID, SYNTHESIS_PARAMETER, SYNTHESIS_UNIT, SYNTHESIS_MIN_VALUE, SYNTHESIS_MAX_VALUE) VALUES ({PRODUCT_ID}, '{SYNTHESIS_PARAMETER}', '{SYNTHESIS_UNIT}', {SYNTHESIS_MIN_VALUE}, {SYNTHESIS_MAX_VALUE});".format(
                        PRODUCT_ID = pid,
                        SYNTHESIS_PARAMETER = row[0],
                        SYNTHESIS_UNIT = row[1],
                        SYNTHESIS_MIN_VALUE = val_min,
                        SYNTHESIS_MAX_VALUE = val_max
                    )
                    outQueries.append(parameter)

        return outQueries

    def form_insert_queries(dataDict: dict) -> list[str]:
        outQueries = []

        main = dataDict.get("main")
        pid = main[AddQuery.DATA_DICT_MAIN_ID["productID"]]
        doi = main[AddQuery.DATA_DICT_MAIN_ID["doi"]]
        year = main[AddQuery.DATA_DICT_MAIN_ID["year"]]
        journal = main[AddQuery.DATA_DICT_MAIN_ID["journal"]]

        if journal and year:
            bib_source = "INSERT INTO bib_source(JOURNAL, YEAR, IMPACT) VALUES ('{journal}', {year}, {impact});".format(journal = journal, year = year, impact = main[AddQuery.DATA_DICT_MAIN_STRUCT["impact"]])
            outQueries.append(bib_source)

        if doi:
            bibliography = "INSERT INTO bibliography(DOI, INTERNAL_CIPHER, URL, YEAR, JOURNAL) VALUES ('{DOI}', '{INTERNAL_CIPHER}', '{URL}', {YEAR}, '{JOURNAL}');".format(
                DOI = doi,
                INTERNAL_CIPHER = main[AddQuery.DATA_DICT_MAIN_STRUCT["cipher"]], 
                URL = main[AddQuery.DATA_DICT_MAIN_STRUCT["url"]], 
                YEAR = year, 
                JOURNAL = journal
            )
        
            outQueries.append(bibliography)

        outQueries = outQueries + AddQuery.form_insert_queries_sub(dataDict)

        if pid:
            a_min, a_max = AddQuery.decompose_range(main[AddQuery.DATA_DICT_MAIN_STRUCT["a_param"]])
            src_mix_min, src_mix_max = AddQuery.decompose_range(main[AddQuery.DATA_DICT_MAIN_STRUCT["mix_time"]])
            synth_time_min, synth_time_max = AddQuery.decompose_range(main[AddQuery.DATA_DICT_MAIN_STRUCT["synth_time"]])
            synth_prod = "INSERT INTO synthesis_product (PRODUCT, PRODUCT_ID, DOI, A_PARAMETER_MAX, A_PARAMETER_MIN, MIXING_METHOD, SOURCE_MIX_TIME_MIN, SOURCE_MIX_TIME_MAX, METHOD, GAS, SYNTHESIS_TIME_MIN, SYNTHESIS_TIME_MAX, FEATURE, CONTRIBUTOR, COMMENTS) VALUES ('{PRODUCT}', {PRODUCT_ID}, '{DOI}', {A_PARAMETER_MAX}, {A_PARAMETER_MIN}, '{MIXING_METHOD}', {SOURCE_MIX_TIME_MIN}, {SOURCE_MIX_TIME_MAX}, '{METHOD}', '{GAS}', {SYNTHESIS_TIME_MIN}, {SYNTHESIS_TIME_MAX}, '{FEATURE}', '{CONTRIBUTOR}', '{COMMENTS}');".format(
                PRODUCT = main[AddQuery.DATA_DICT_MAIN_STRUCT["product"]], 
                PRODUCT_ID = pid,
                DOI = doi,
                A_PARAMETER_MAX = a_max,
                A_PARAMETER_MIN = a_min,
                MIXING_METHOD = main[AddQuery.DATA_DICT_MAIN_STRUCT["mix_method"]],
                SOURCE_MIX_TIME_MIN = src_mix_min,
                SOURCE_MIX_TIME_MAX = src_mix_max,
                METHOD = main[AddQuery.DATA_DICT_MAIN_STRUCT["method"]],
                GAS = main[AddQuery.DATA_DICT_MAIN_STRUCT["gas"]],
                SYNTHESIS_TIME_MIN = synth_time_min,
                SYNTHESIS_TIME_MAX = synth_time_max,
                FEATURE = main[AddQuery.DATA_DICT_MAIN_STRUCT["feature"]],
                CONTRIBUTOR = main[AddQuery.DATA_DICT_MAIN_STRUCT["contributor"]],
                COMMENTS = main[AddQuery.DATA_DICT_MAIN_STRUCT["comments"]]
            )
        
            outQueries.append(synth_prod)

        return outQueries

    def decompose_range(possibleRange: str) -> list:
        possibleRange = possibleRange.strip()
        if possibleRange[0] == '[':
            possibleRange = possibleRange[1:-1]
            return list(map(str.strip, possibleRange.split(',')))
        else:
            possibleRange = possibleRange.strip()
            return possibleRange, possibleRange