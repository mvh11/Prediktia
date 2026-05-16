import { HomeLanding } from "@/components/home/HomeLanding";
import { getHomePageData } from "@/lib/home/getHomePageData";

export default async function Home() {
  const data = await getHomePageData();
  return <HomeLanding data={data} />;
}
