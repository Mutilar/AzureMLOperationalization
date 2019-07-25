import json
import file_handler as fh

TAB = "    "


class Notebook:


    def __init__(self, notebook_str):
        """ Loads a notebook into a JSON object.
        """

        self.notebook_json = json.loads(notebook_str)


    def __str__(self):
        """ Returns a formatted JSON string.
        """

        return str(json.dumps(self.notebook_json, indent=1))


    def get_cells(self, position = "FIRST"):
        """ Collecting a list of indices of cells to inject/indent in.
        """

        indices = []
        if position == "FIRST":
            counter = 0
            while self.notebook_json["cells"][counter]["cell_type"] != "code":
                counter += 1
            indices.append(counter)
        elif position == "LAST":
            counter = -1
            while self.notebook_json["cells"][counter]["cell_type"] != "code":
                counter -= 1
            indices.append(counter)
        elif position == "EVERY":
            indices = []
            counter = 0
            for cell in self.notebook_json["cells"]:
                if cell["cell_type"] == "code":
                    indices.append(counter)
                counter += 1
        return indices


    def indent_code(self, cells = []):
        """ Adds a tab before every line of code.
        """

        for cell in cells:
            counter = 0
            cell_size = len(self.notebook_json["cells"][cell]["source"])
            while counter < cell_size:
                line = self.notebook_json["cells"][cell]["source"][counter]
                line = TAB + line
                self.notebook_json["cells"][cell]["source"][counter] = line
                counter += 1


    def unindent_code(self, cells = []):
        """ Removes a tab before every line of code from a collection of specified code cells.
        This is not a smart function, and should only be called if indent_code is called first.
        """

        for cell in cells:
            counter = 0
            cell_size = len(self.notebook_json["cells"][cell]["source"])
            while counter < cell_size:
                line = self.notebook_json["cells"][cell]["source"][counter]
                line = line[len(TAB):]
                self.notebook_json["cells"][cell]["source"][counter] = line
                counter += 1


    def inject_code(self, cells = [], position = "FRONT", code = []):
        """ Adds a collection of lines of code at the front of back of a collection of specified code cells
        """

        for cell in cells:
            if position == "FRONT":
                self.notebook_json["cells"][cell]["source"] = ["#INJECTED CODE START\n"] + code + ["#INJECTED CODE END\n"] + self.notebook_json["cells"][cell]["source"]
            elif position == "BACK":
                self.notebook_json["cells"][cell]["source"][-1] = self.notebook_json["cells"][cell]["source"][-1] + "\n"
                self.notebook_json["cells"][cell]["source"] = self.notebook_json["cells"][cell]["source"] + ["#INJECTED CODE START\n"] + code + ["#INJECTED CODE END\n"]


    def scrub_code(self, cells = []):
        """ Removes all lines of code injected by inject_code from a collection of specified code cells
        """

        for cell in cells:
            while "#INJECTED CODE START\n" in self.notebook_json["cells"][cell]["source"]
                injection_start = self.notebook_json["cells"][cell]["source"].index("#INJECTED CODE START\n")
                injection_end = self.notebook_json["cells"][cell]["source"].index("#INJECTED CODE END\n")
                del self.notebook_json["cells"][cell]["source"][injection_start:injection_end]
