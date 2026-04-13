from models.user_stats import SolvedUserData


class SolvedAcUserParser:
    def parse(self, information: dict) -> SolvedUserData:
        class_value = information["class"] * 3
        if information["classDecoration"] == "silver":
            class_value += 1
        if information["classDecoration"] == "gold":
            class_value += 2
        return SolvedUserData(
            solvedCount=information["solvedCount"],
            voteCount=information["voteCount"],
            tier=information["tier"],
            classValue=class_value,
        )
