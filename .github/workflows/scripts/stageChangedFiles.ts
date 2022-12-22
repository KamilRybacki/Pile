
type GithubActionsInterface = {
  setSecret: (arg0: { name: string; value: string[]; }) => void;
}

module.exports = (
  candidates: Array<string>,
  label: string,
  githubActions: GithubActionsInterface
) => {
  if (candidates.length > 0) {
    console.log(`Changed ${label} files: ${candidates}`)
    githubActions.setSecret({
      name: `CHANGED_${label.toUpperCase()}_FILES`,
      value: candidates
    })
  } else {
    console.log(`No changed ${label} files`)
  }
};
