
# coding: utf-8

# In[ ]:


# -------------- Apache Sparkについて -------------- 


# In[ ]:


"""
Apache Sparkは、簡単に言うと 並列分散処理基盤である Hadoop の MapReduce フレームワークに相当するもの。

MapReduce処理は Map処理→Reduce処理 ごとに基本的には HDFS に書き込んでいる。
その場合、
　・Map処理→Reduce処理が多段になった場合に、I/Oのレイテンシが問題になる
　・機械学習のような、同じデータ（処理結果）を何度も使い回す処理の場合、やはりI/Oが何度も発生し問題になる
といったような問題が発生する。

そこで Apache Spark では “インメモリ”・“RDD”（部分故障への耐性を考慮した分散コレクション） を活用することで
この問題を解決していく。

このRDDは Apache Spark Core として低レイヤを担っており、
Apache Spark Core をベースとして
　・Spark SQL
 　（構造化されたデータの処理のためのSparkコンポーネント、構造化されていれば形式に関わらず、DataFrameとして読み込むことでSQL的にデータを扱える）
 ・Spark Streaming
 　（ストリームデータを処理するためのSparkコンポーネント）
 ・MLib
 　（機械学習のためのSparkコンポーネント、最新ではSpark SQLに入っている？）
 ・GraphX
 　（大容量のグラフデータを並列分散環境で処理するためのコンポーネント、ナレッジグラフ、マーケティングリレーション、経路探索、ページランク分析など特定の分野に対しては非常に有効）
といったコンポーネントが用意されている。
"""


# In[ ]:


# -------------- 前提としてやるべきこと -------------- 


# In[ ]:


"""
SparkSessionをimportする
"""
from pyspark.sql import SparkSession


# In[ ]:


"""
SparkSessionでセッションを作成する。
なお、すでに同一名のセッションが存在する場合は既存セッションを取得する。
"""
spark = SparkSession   .builder   .master('yarn')   .appName('learning-spark')   .getOrCreate()


# In[ ]:


"""
Dataprocではデータエクスポートの一時ディレクトリとして、GCSを利用することができる。
特にBigQueryコネクタを利用して取得する際には重要になる
"""
bucket = "〜"
spark.conf.set('temporaryGcsBucket', bucket)


# In[ ]:


# -------------- Spark SQL -------------- 


# In[ ]:


# -------------- DataFrame と RDD -------------- 


# In[ ]:


"""
pyspark.sql で利用できるデータ構造としては、大きく DataFrame と RDD がある。
RDD（Resilient Distributed Dataset）は Spark Core で提供されており、Sparkの中心となるデータ構造であり、これまでSpark SQLではRDDがメインで使われていた。

しかしその後、pyspark.sqlではより上位のデータ抽象化として DataFrame が登場した。RDDは「Sparkが目的をどう実現しているか」を表すのに対して、DataFrameは「Sparkは意味的に何をしているのか」が表現しやすい。

DataFrameによって、様々な形式のデータ（CSVなどのファイル、RDBやBigQueryなど）を、まるでRDBに対してSQLで操作するように扱うことができると共に、言語間（ScalaとPython、Rなど）での実装の差を大きく減らすことができた。

RDDに対してDataFrameは、位置付けとしてより高レイヤなオブジェクトであり、filterやjoinなどの便利なメソッドが用意されている。
用意されているAPIでできる処理は、DataFrameの方がパフォーマンスも出せるため、今後は原則としてDataFrameで処理を組んでいくことが基本指針となる。

また、RDDへの変換・RDDからの変換も可能であり、以下のような要件が出てきた場合には、RDDに変換して対応していく、ということになる。
　・RDDで構築された3rd Partyのパッケージを利用する場合
　・Sparkにクエリの実行方法を正確に指示したい場合

※   また Spark としては 「Datasets」 という型定義できるデータ構造もあるが、
    コンパイルを伴う Java か Scala でしか利用できない。
"""


# In[ ]:


"""
DataFrameは、sparkセッションを使って
　・データファイルをreadする
　・他のDataFrameをフィルタリングする
などした場合に生成できる。（SparkSessionが安全に、分散処理を実現してくれる）

DataprocではデフォルトでGCSコネクタが入っており、
pathに “gs://〜” と対象ファイルを指定することで、自然に取得することができる。
"""
tsv_path="gs://〜.tsv"
df = spark.read.csv(tsv_path, sep=r'\t', header=True)


# In[ ]:


"""
limit や selectで、SQLライクにデータを扱える
"""
df.limit(5).select("text").show()
print(df.count())
print(df.columns)


# In[ ]:


"""
RDDへの変換は df.rdd で行える。
ただし RDD[Row] 形式で返ってくるので、map内ではさらにフィールドを指定してやる必要あり （selectで特定フィールドに絞ってもダメ）
https://stackoverflow.com/questions/40653567/attribute-error-split-on-spark-sql-python-using-lambda
"""
df.limit(4).select('idx_id').rdd.map(lambda line: line.idx_id.split("_")).collect()


# In[ ]:


"""
RDDからDataFrameの変換も行える
https://blog.imind.jp/entry/2019/06/23/004922
"""
from pyspark.sql import types as T, functions as F

# スキーマの設定
schema = T.StructType([
    T.StructField('col1', T.StringType()),
    T.StructField('col2', T.LongType())
])

# 先ほどエラーになったrdd
rdd2 = sc.parallelize([
    Row(col1=None, col2=1),
    Row(col1=None, col2=2)
])

# schemaを指定してDataFrameに変換
df2 = spark.createDataFrame(rdd2, schema)
df2.collect()


# In[ ]:


"""
Spark SQLをjupyterで触っていて、selectなどを使っていると「あれ？こんなに早くselectできるの？」と思う場面があるかもしれない。

limitやselectなどのfuncを呼んでいる際には処理の流れを組んでいる状態
（これらの処理は「Transformations」と呼ばれる場合も。
　RDDで言うと、https://ex-ture.com/blog/2019/06/27/learn-databricks-spark-rdd-operations/
    map
    flatMap
    filter
    union
    intersection
    subtrct
    distinct
　　などがあり、DataFrameで言うと https://www.learningjournal.guru/courses/spark/spark-foundation-training/spark-dataframe-transformations/
     select
    groupby
　などがある）

それが実際に処理されるのは「Actions」という“結果を取得するfunc”が呼ばれたときに初めて実行される。
RDDで言うと、https://ex-ture.com/blog/2019/06/27/learn-databricks-spark-rdd-operations/
    collect
    count
    first
    take
    reduce
    takeOrdered
    top
などがあり、DataFrameで言うと 
    show
や、各種出力が挙げられる。

Actionsの多くは、結果としてPythonの配列を返すことも多い。
（逆を言うと、RDDはSparkの型なので、通常のPythonのfunc処理を使おうとする際には注意が必要）
"""


# In[ ]:


"""
DataFrameのUDF
RDDではmapやfilterで各レコードごとに処理をしていくが、
DataFrameではUDF（ユーザー定義関数）を使って処理をしていく。
https://spark.apache.org/docs/2.4.0/api/python/_modules/pyspark/sql/udf.html
"""
class JapaneseTokenizer(object):
    def __init__(self):
        self.mecab = MeCab.Tagger("-Ochasen -d /usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ipadic-neologd")
        self.mecab.parseToNode('')
 
    def split(self, text):
        node = self.mecab.parseToNode(text)
        words = []
        while node:
            if node.surface:
                words.append(node.surface.decode("UTF-8"))
            node = node.next
        return words
def tokenize(text):
    tokenizer = JapaneseTokenizer()
    return tokenizer.split(text)
def tokenize_and_create_rdd(text):
    return ','.join(tokenize(text.encode("UTF-8")))

tokenize_udf = F.udf(tokenize_and_create_rdd, T.StringType()) #既存のdefを第一引数に、第二引数に戻り値のSpark型を入れて教えてあげる

df_wakati_result = df_wakati_base    .withColumn("wakati", tokenize_udf((F.col("text"))))


# In[ ]:


"""
DataFrameへのレコードの追加
withColumnを利用する。第一引数に結果として保存するキー名、第二引数に処理を指定する。
"""
df_add_result = df_base    .withColumn("add_tdate", F.col("tdate"))


# In[ ]:


"""
DataFrameの定数列追加
一律の絡むを追加するには、F.litを利用する
"""
df_convert_result = df_base
    .withColumn("today", F.lit("today"))


# In[ ]:


"""
DataFrameのカラム型変換
"""
# Date
df_convert_result1 = df_base
    .withColumn("tdate", F.lit(str_yyyymmdd_to_date(target_date)))    .withColumn("tdate", F.lit(F.col("tdate").cast("date")))
    
# Timestamp
df_wakati_result2 = df_base    .withColumn("created_at", df_wakati_base.created_at.cast(T.TimestampType()))


# In[ ]:


# -------------- BigQuery Connector -------------- 


# In[ ]:


"""
dataproc-mecab-init-shellで作成した環境では、BigQueryコネクタをinstallしているため、
BigQueryの読み込み、書き込みができる。
https://cloud.google.com/dataproc/docs/tutorials/bigquery-connector-spark-example?hl=ja
"""


# In[ ]:


# GCPのサンプル
# Load data from BigQuery.
words = spark.read.format('bigquery')   .option('table', 'bigquery-public-data:samples.shakespeare')   .load()
words.createOrReplaceTempView('words')

# Perform word count.
word_count = spark.sql(
    'SELECT word, SUM(word_count) AS word_count FROM words GROUP BY word')
word_count.show()
word_count.printSchema()

# Saving the data to BigQuery
word_count.write.format('bigquery').option('table', 'wordcount_dataset.wordcount_output').save()


# In[ ]:


"""
既存のTableへの追加
（上記のサンプルはテーブルの新規作成にあたり、既存への追加ではエラーになる。）
"""
# df_base\
#     .write\
#     .format('bigquery')\
#     .mode('append')\ #モードをappendに切り替える
#     .option('table', '{0}.{1}'.format(bigquery_dataset, bigquery_save_table))\
#     .option('partitionType', 'DAY')\  #パーティションタイプを設定する
#     .option('partitionField', 'tdate')\  #パーティションに利用するフィールドを指定する
#     .save()


# In[ ]:


# -------------- MySQL Connector -------------- 


# In[ ]:


"""
Dataprocで、MySQLへつなぐ方法としてdataproc-mecab-init-shellで作成した環境では
Apache Hiveを応用し、
　・enable-cloud-sql-hive-metastore=false （本来のメタストアは有効にしない）
 ・additional-cloud-sql-instances=${CLOUDSQL_PROJECT_ID}:${REGION}:${CLOUDSQL_INSTANCE_NAME}=tcp:5432 （追加で接続したいDBを指定）
することで、localhost:5432 で接続できるようにしている。

また、クライアントとしては JDBC（Java Database Connectivity） をインストールしている。
これで、他のファイルからの読み込みと同じように操作できる
"""


# In[ ]:


options = {
    "url":"jdbc:mysql://127.0.01:5432/{スキーマ名}",
    "driver":"com.mysql.jdbc.Driver",
    "dbtable":"{テーブル名}",
    "user":"{ユーザー名}",
    "password":"{パスワード}"
}

df = spark.read.format("jdbc").options(**options).load()
df.limit(5).show()


# In[ ]:


# -------------- MeCabを使った形態素解析 -------------- 


# In[ ]:


"""
dataproc-mecab-init-shellで作成した環境では、MeCabのインストールも行なっている。（拡張辞書入り）
MeCabでTokenizerを作り、RDDのmapで実行することで処理が可能。
"""


# In[ ]:


import MeCab
class JapaneseTokenizer(object):
    def __init__(self):
        self.mecab = MeCab.Tagger("-Ochasen -d /usr/lib/x86_64-linux-gnu/mecab/dic/mecab-ipadic-neologd")
        self.mecab.parseToNode('')
 
    def split(self, text):
        node = self.mecab.parseToNode(text)
        words = []
        while node:
            if node.surface:
                words.append(node.surface.decode("UTF-8"))
            node = node.next
        return words

def tokenize(text):
    tokenizer = JapaneseTokenizer()
    return tokenizer.split(text)


# In[ ]:


"""
tokenizeのテスト実行
"""
print(tokenize(u'テスト文字列'.encode('utf-8')))


# In[ ]:


"""
本実行（テストとして5件にフィルタしている） RDD版
"""
df = spark.read.csv(tsv_path, sep=r'\t', header=True)
results = df.limit(5).select("text").rdd.map(lambda x: ','.join(tokenize(x.text.encode('utf-8'))))


# In[ ]:


"""
本実行 DataFrame版
"""
def tokenize_and_create_rdd(text):
    return ','.join(tokenize(text.encode("UTF-8")))

tokenize_udf = F.udf(tokenize_and_create_rdd, T.StringType())


# In[ ]:


"""
結果チェック
"""
for i, result in enumerate(results.take(5)):
    print(result)

