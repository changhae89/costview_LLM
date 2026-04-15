import seedChain from "@/data/chains/CHN_RUA_001.json";
import type { ChainEvent } from "@/lib/types";

describe("ChainEvent seed shape", () => {
  it("matches the ChainEvent contract for CHN_RUA_001", () => {
    const chainEvent: ChainEvent = seedChain;

    expect(chainEvent.chain_id).toBe("CHN_RUA_001");
    expect(chainEvent.storytelling.headline).toBe("전쟁이 밥상을 흔든다");
    expect(chainEvent.substitute_recommendations).toHaveLength(2);
  });
});
