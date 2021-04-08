import pandas
import networkx
import datetime
import requests
from typing import List
from prefect import task
from prefect.engine.results import LocalResult


@task
def extract_wgcna(filename: str) -> List[str]:
    with open(filename, "r") as f:
        return list(filter(None, f.read().split("\n")))


@task(checkpoint=True, result=LocalResult(dir="result"), cache_for=datetime.timedelta(days=1))
def get_stringdb() -> pandas.DataFrame:
    df = pandas.read_csv(
        "https://stringdb-static.org/download/protein.links.detailed.v11.0/9606.protein.links.detailed.v11.0.txt.gz",
        sep=" "
    )[["protein1", "protein2", "experimental", "database"]]
    df_names = pandas.read_csv(
        "https://stringdb-static.org/download/protein.info.v11.0/9606.protein.info.v11.0.txt.gz",
        sep="\t"
    )[["protein_external_id", "preferred_name"]]

    df_renamed_p1 = pandas.merge(
        df, df_names, "left", left_on="protein1", right_on="protein_external_id"
    ).rename(columns={"preferred_name": "preferredName_A"}
    )[["preferredName_A", "protein2", "experimental", "database"]]

    df_renamed = pandas.merge(
        df_renamed_p1, df_names, "left", left_on="protein2", right_on="protein_external_id"
    ).rename(columns={"preferred_name": "preferredName_B"}
    )[["preferredName_A", "preferredName_B", "experimental", "database"]]

    return df_renamed


@task
def extract_string_scores(identifiers: List[str], db: pandas.DataFrame) -> pandas.DataFrame:
    df_genes = db[  
        db.preferredName_A.isin(identifiers) & db.preferredName_B.isin(identifiers)]

    df_genes["escore"] = df_genes["experimental"] / 1000.0
    df_genes["dscore"] = df_genes["database"] / 1000.0

    return df_genes[["preferredName_A", "preferredName_B", "dscore", "escore"]]


@task
def filter_reliable_interactions(
        node_df: pandas.DataFrame) -> pandas.DataFrame:
    filters = (
        (node_df.escore >= 0.5) |
        ((node_df.escore >= 0.3) & (node_df.dscore >= 0.9))
    )
    return node_df[filters]


@task
def build_interaction_graph(pattern_df: pandas.DataFrame) -> networkx.Graph:
    return networkx.from_pandas_edgelist(
        pattern_df, "preferredName_A", "preferredName_B", edge_attr=True)


@task(result=LocalResult(dir="result"))
def save_output(graph: networkx.Graph) -> dict:
    return networkx.readwrite.json_graph.cytoscape_data(graph)