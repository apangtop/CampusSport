export function matchState(rounds, teamA, teamB, maxRounds) {
  const wins = { [teamA]: 0, [teamB]: 0 }
  const result = { valid: true, complete: false, winner: null, wins, played: 0, error: '' }
  if (!teamA || !teamB || teamA === teamB || ![3, 5].includes(maxRounds)) {
    return { ...result, valid: false, error: '请选择不同的有效队伍及赛制' }
  }
  const needed = (maxRounds + 1) / 2
  let gap = false
  for (let index = 0; index < rounds.length; index++) {
    const round = rounds[index]
    if (!round.winner) { gap = true; continue }
    if (index >= maxRounds || round.number !== index + 1 || gap) {
      return { ...result, valid: false, error: '局次须从第一局开始连续填写' }
    }
    if (result.winner) return { ...result, valid: false, error: '比赛已分出胜负，不能继续填写后续局次' }
    if (round.winner !== teamA && round.winner !== teamB) {
      return { ...result, valid: false, error: '局次胜者须属于当前对阵队伍' }
    }
    wins[round.winner]++
    result.played++
    if (wins[round.winner] === needed) {
      result.winner = round.winner
      result.complete = true
    }
  }
  return result
}

export function trimUnplayedRounds(rounds, teamA, teamB, maxRounds) {
  const wins = { [teamA]: 0, [teamB]: 0 }
  const needed = (maxRounds + 1) / 2
  let stopped = false
  for (const round of rounds) {
    if (stopped) { if (round.winner) round.winner = ''; continue }
    if (!round.winner) { stopped = true; continue }
    wins[round.winner]++
    if (wins[round.winner] === needed) stopped = true
  }
}
