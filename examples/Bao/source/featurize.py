import numpy as np

JOIN_TYPES = ["Nested Loop", "Hash Join", "Merge Join"]

LEAF_TYPES = ["Seq Scan", "Index Scan", "Index Only Scan", "Bitmap Index Scan"]
ALL_TYPES = JOIN_TYPES + LEAF_TYPES

SPARK_LEAF_TYPES = ["org.apache.spark.sql.execution.FileSourceScanExec"]
SPARK_JOIN_TYPES = ["org.apache.spark.sql.execution.joins.BroadcastHashJoinExec",
                    "org.apache.spark.sql.execution.joins.SortMergeJoinExec",
                    "org.apache.spark.sql.execution.joins.BroadcastNestedLoopJoinExec"]
ALL_SPARK_TYPES = SPARK_LEAF_TYPES + SPARK_JOIN_TYPES


class TreeBuilderError(Exception):
    def __init__(self, msg):
        self.__msg = msg


def is_join(node, is_spark=False):
    if is_spark:
        return node["class"] in SPARK_JOIN_TYPES
    else:
        return node["Node Type"] in JOIN_TYPES


def is_scan(node, is_spark=False):
    if is_spark:
        return node["class"] in SPARK_LEAF_TYPES
    else:
        return node["Node Type"] in LEAF_TYPES


class TreeBuilder:
    def __init__(self, stats_extractor, relations, is_spark=False):
        self.__stats = stats_extractor
        self.__relations = sorted(relations, key=lambda x: len(x), reverse=True)
        self.is_spark = is_spark

    def __relation_name(self, node):
        if self.is_spark:
            return node["tableIdentifier"]["table"]
        else:
            if "Relation Name" in node:
                return node["Relation Name"]

            if node["Node Type"] == "Bitmap Index Scan":
                # find the first (longest) relation name that appears in the index name
                name_key = "Index Name" if "Index Name" in node else "Relation Name"
                if name_key not in node:
                    print(node)
                    raise TreeBuilderError("Bitmap operator did not have an index name or a relation name")
                for rel in self.__relations:
                    if rel in node[name_key]:
                        return rel

                raise TreeBuilderError("Could not find relation name for bitmap index scan")

            raise TreeBuilderError("Cannot extract relation type from node")

    def __featurize_join(self, node):
        assert is_join(node, self.is_spark)
        arr = np.zeros(len(ALL_TYPES))

        if self.is_spark:
            arr[ALL_SPARK_TYPES.index(node["class"])] = 1
        else:
            arr[ALL_TYPES.index(node["Node Type"])] = 1
        return np.concatenate((arr, self.__stats(node)))

    def __featurize_scan(self, node):
        assert is_scan(node, self.is_spark)
        arr = np.zeros(len(ALL_TYPES))

        if self.is_spark:
            arr[ALL_SPARK_TYPES.index(node["class"])] = 1
        else:
            arr[ALL_TYPES.index(node["Node Type"])] = 1
        return (np.concatenate((arr, self.__stats(node))),
                self.__relation_name(node))

    def plan_to_feature_tree(self, plan):
        children = plan["Plans"] if "Plans" in plan else []

        if len(children) == 1:
            return self.plan_to_feature_tree(children[0])

        if is_join(plan, is_spark=self.is_spark):
            assert len(children) == 2
            my_vec = self.__featurize_join(plan)
            left = self.plan_to_feature_tree(children[0])
            right = self.plan_to_feature_tree(children[1])
            return (my_vec, left, right)

        # if plan["Node Type"] == "BitmapAnd":
        #     assert len(children) == 2
        #     left = self.plan_to_feature_tree(children[0])
        #     right = self.plan_to_feature_tree(children[1])
        #     return (np.array([0]), left, right)

        if is_scan(plan, is_spark=self.is_spark):
            assert not children
            return self.__featurize_scan(plan)

        raise TreeBuilderError("Node wasn't transparent, a join, or a scan: " + str(plan))


def norm(x, lo, hi):
    return (np.log(x + 1) - lo) / (hi - lo)


def get_buffer_count_for_leaf(leaf, buffers):
    total = 0
    if "Relation Name" in leaf:
        total += buffers.get(leaf["Relation Name"], 0)

    if "Index Name" in leaf:
        total += buffers.get(leaf["Index Name"], 0)

    return total


class StatExtractor:
    def __init__(self, fields, mins, maxs):
        self.__fields = fields
        self.__mins = mins
        self.__maxs = maxs

    def __call__(self, inp):
        res = []
        for f, lo, hi in zip(self.__fields, self.__mins, self.__maxs):
            if f not in inp:
                res.append(0)
            else:
                res.append(norm(inp[f], lo, hi))
        return res


def get_plan_stats(data, is_spark=False):
    costs = []
    rows = []
    bufs = []

    def recurse(n, buffers=None, is_spark=False):
        if is_spark:
            costs.append(0)
            rows.append(n["rowCount"])
        else:
            costs.append(n["Total Cost"])
            rows.append(n["Plan Rows"])

        if "Buffers" in n:
            bufs.append(n["Buffers"])

        if "Plans" in n:
            for child in n["Plans"]:
                recurse(child, is_spark=is_spark)

    for plan in data:
        recurse(plan["Plan"], buffers=plan.get("Buffers", None), is_spark=is_spark)

    costs = np.array(costs)
    rows = np.array(rows)
    bufs = np.array(bufs)

    costs = np.log(costs + 1)
    rows = np.log(rows + 1)
    bufs = np.log(bufs + 1)

    costs_min = np.min(costs)
    costs_max = np.max(costs)
    rows_min = np.min(rows)
    rows_max = np.max(rows)
    bufs_min = np.min(bufs) if len(bufs) != 0 else 0
    bufs_max = np.max(bufs) if len(bufs) != 0 else 0

    if len(bufs) != 0:
        return StatExtractor(
            ["Buffers", "Total Cost", "Plan Rows"],
            [bufs_min, costs_min, rows_min],
            [bufs_max, costs_max, rows_max]
        )
    else:
        return StatExtractor(
            ["Total Cost", "Plan Rows"],
            [costs_min, rows_min],
            [costs_max, rows_max]
        )


def get_all_relations(data):
    all_rels = []

    def recurse(plan):
        if "Relation Name" in plan:
            yield plan["Relation Name"]

        if "Plans" in plan:
            for child in plan["Plans"]:
                yield from recurse(child)

    for plan in data:
        all_rels.extend(list(recurse(plan["Plan"])))

    return set(all_rels)


def get_all_relations_spark(data):
    all_rels = []

    def recurse(plan):
        if "tableIdentifier" in plan:
            yield plan["tableIdentifier"]["table"]

        if "Plans" in plan:
            for child in plan["Plans"]:
                yield from recurse(child)

    for plan in data:
        all_rels.extend(list(recurse(plan["Plan"])))

    return set(all_rels)


def get_featurized_trees(data):
    all_rels = get_all_relations(data)
    stats_extractor = get_plan_stats(data)

    t = TreeBuilder(stats_extractor, all_rels)
    trees = []

    for plan in data:
        tree = t.plan_to_feature_tree(plan)
        trees.append(tree)

    return trees


def _attach_buf_data(tree):
    if "Buffers" not in tree:
        return

    buffers = tree["Buffers"]

    def recurse(n):
        if "Plans" in n:
            for child in n["Plans"]:
                recurse(child)
            return

        # it is a leaf
        n["Buffers"] = get_buffer_count_for_leaf(n, buffers)

    recurse(tree["Plan"])


class TreeFeaturizer:
    def __init__(self, is_spark=False):
        self.__tree_builder = None
        self.is_spark = is_spark

    def fit(self, trees):
        for t in trees:
            _attach_buf_data(t)
        if self.is_spark:
            all_rels = get_all_relations_spark(trees)
        else:
            all_rels = get_all_relations(trees)
        stats_extractor = get_plan_stats(trees, is_spark=self.is_spark)
        self.__tree_builder = TreeBuilder(stats_extractor, all_rels, self.is_spark)

    def transform(self, trees):
        for t in trees:
            _attach_buf_data(t)
        return [self.__tree_builder.plan_to_feature_tree(x["Plan"]) for x in trees]

    def num_operators(self):
        return len(ALL_TYPES)
