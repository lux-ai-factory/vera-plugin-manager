from cli_wrapper import CLIWrapper
from wheel_filename import WheelFilename


class DevpiClient:
    def __init__(self, base_url: str, index: str, user: str, password: str):
        self.devpi = CLIWrapper("devpi")
        self.uv = CLIWrapper("uv")
        self.base_url = base_url
        self.index = index
        self.full_index_url = f"{self.base_url}/{self.index}"
        self.user = user
        self.password = password
        self._initialized = False

    def _initialize_devpi(self):
        if not self._initialized:
            self.devpi.use(self.full_index_url)
            self.devpi.login(self.user, password=self.password, y=True)
            self._initialized = True

    def list_packages(self) -> dict[str, str]:
        """Returns a dictionary of {package_name: latest_version}"""
        self._initialize_devpi()

        packages_output = self.devpi.list()
        if not packages_output:
            return {}

        package_names = list(filter(None, packages_output.split("\n")))

        result = {}
        for pkg in package_names:
            try:
                pkg_info = self.devpi.list(pkg)
                whl = WheelFilename.parse(pkg_info.strip())

                if whl.version:
                    version = whl.version
                    result[pkg] = version
                else:
                    result[pkg] = "latest"
            except Exception:
                result[pkg] = "latest"

        return result

    def install_package(self, package_name: str, version: str = None):
        install_target = package_name
        if version:
            install_target = f"{package_name}=={version}"

        return self.uv.pip(
            "install",
            install_target,
            **{"extra-index-url": f"{self.full_index_url}/+simple/"}
        )