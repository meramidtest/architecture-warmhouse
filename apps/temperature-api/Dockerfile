FROM mcr.microsoft.com/dotnet/sdk:9.0 AS build

ARG BUILD_CONFIGURATION=Debug
ARG DOTNET_ARCH=amd64

WORKDIR /src
COPY . .

RUN --mount=type=cache,id=nuget,target=/root/.nuget/packages \
    dotnet restore

RUN --mount=type=cache,id=nuget,target=/root/.nuget/packages \
    dotnet publish -c ${BUILD_CONFIGURATION} --self-contained true -r linux-${DOTNET_ARCH} -o /app

WORKDIR /src
RUN dotnet new tool-manifest --force
RUN dotnet tool install Swashbuckle.AspNetCore.Cli --version 9.0.3 --local
RUN dotnet tool run swagger tofile --output swagger.json /app/temperature-api.dll v1


FROM mcr.microsoft.com/dotnet/aspnet:9.0 AS final

WORKDIR /app
COPY --from=build /app /app
COPY --from=build /root/.dotnet /root/.dotnet

ENV ASPNETCORE_URLS=http://+:8081
EXPOSE 8081

ENTRYPOINT ["dotnet", "temperature-api.dll"]
